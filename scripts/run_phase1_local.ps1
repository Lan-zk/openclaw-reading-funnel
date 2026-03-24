param(
  [Parameter(Mandatory = $true)] [string] $Config,
  [Parameter(Mandatory = $true)] [string] $WindowStart,
  [Parameter(Mandatory = $true)] [string] $WindowEnd,
  [string] $RunId = (Get-Date -Format "yyyyMMddHHmmss"),
  [string] $BaseDir = "runs"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonBin = if ($env:PYTHON_BIN) { $env:PYTHON_BIN } else { "python" }
$runBase = if ([System.IO.Path]::IsPathRooted($BaseDir)) { $BaseDir } else { Join-Path $repoRoot $BaseDir }
$runDir = Join-Path $runBase $RunId
New-Item -ItemType Directory -Force -Path $runDir | Out-Null

function Invoke-Step {
  param(
    [string] $Name,
    [string[]] $ArgumentList
  )
  & $pythonBin @ArgumentList
  if ($LASTEXITCODE -ne 0) {
    throw "Step $Name failed with exit code $LASTEXITCODE"
  }
}

function Test-CanContinue {
  param([string] $ManifestPath)
  $manifest = Get-Content -Raw -Encoding UTF8 $ManifestPath | ConvertFrom-Json
  if (-not $manifest.continue_recommended) {
    return $false
  }
  foreach ($artifact in $manifest.output_artifacts) {
    if ($artifact.artifact_role -eq "PRIMARY" -and $artifact.consumable_by_downstream) {
      return $true
    }
  }
  return $false
}

$sourceDir = Join-Path $runDir "source-fetch"
Invoke-Step "source-fetch" @(
  (Join-Path $repoRoot "skills\source-fetch\run.py"),
  "--config", $Config,
  "--run-id", $RunId,
  "--window-start", $WindowStart,
  "--window-end", $WindowEnd,
  "--output-dir", $sourceDir
)
$sourceManifest = Join-Path $sourceDir "step-manifest.json"

if (Test-CanContinue $sourceManifest) {
  $normalizeDir = Join-Path $runDir "candidate-normalize"
  Invoke-Step "candidate-normalize" @(
    (Join-Path $repoRoot "skills\candidate-normalize\run.py"),
    "--run-id", $RunId,
    "--input", (Join-Path $sourceDir "raw-source-items.json"),
    "--upstream-manifest", $sourceManifest,
    "--output-dir", $normalizeDir
  )
  $normalizeManifest = Join-Path $normalizeDir "step-manifest.json"

  if (Test-CanContinue $normalizeManifest) {
    $scoreDir = Join-Path $runDir "candidate-score"
    Invoke-Step "candidate-score" @(
      (Join-Path $repoRoot "skills\candidate-score\run.py"),
      "--run-id", $RunId,
      "--input", (Join-Path $normalizeDir "candidate-items.normalized.json"),
      "--upstream-manifest", $normalizeManifest,
      "--output-dir", $scoreDir
    )
    $scoreManifest = Join-Path $scoreDir "step-manifest.json"

    if (Test-CanContinue $scoreManifest) {
      $clusterDir = Join-Path $runDir "dedup-cluster"
      Invoke-Step "dedup-cluster" @(
        (Join-Path $repoRoot "skills\dedup-cluster\run.py"),
        "--run-id", $RunId,
        "--input", (Join-Path $scoreDir "candidate-items.scored.json"),
        "--upstream-manifest", $scoreManifest,
        "--output-dir", $clusterDir
      )
      $clusterManifest = Join-Path $clusterDir "step-manifest.json"

      if (Test-CanContinue $clusterManifest) {
        $buildDir = Join-Path $runDir "reading-candidate-build"
        Invoke-Step "reading-candidate-build" @(
          (Join-Path $repoRoot "skills\reading-candidate-build\run.py"),
          "--run-id", $RunId,
          "--cluster-plan", (Join-Path $clusterDir "cluster-plan.json"),
          "--candidate-items", (Join-Path $scoreDir "candidate-items.scored.json"),
          "--upstream-manifest", $clusterManifest,
          "--output-dir", $buildDir
        )
      }
    }
  }
}

$reviewDir = Join-Path $runDir "run-review"
Invoke-Step "run-review" @(
  (Join-Path $repoRoot "skills\run-review\run.py"),
  "--run-id", $RunId,
  "--run-dir", $runDir,
  "--output-dir", $reviewDir
)
