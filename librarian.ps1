# Portable local CLI wrapper. Python 3.11+ must be available on PATH.
& python "$PSScriptRoot/librarian.py" @args
exit $LASTEXITCODE
