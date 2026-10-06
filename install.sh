#!/bin/bash

set -e

pushd "$(dirname "$0")" > /dev/null

if [ -n "$VIRTUAL_ENV" ]; then
	PYTHON="$VIRTUAL_ENV/bin/python"
elif command -v python > /dev/null 2>&1; then
	PYTHON="$(command -v python)"
elif command -v python3 > /dev/null 2>&1; then
	PYTHON="$(command -v python3)"
else
	echo "Python not found"
	exit 1
fi

if ! "$PYTHON" -c "import a" > /dev/null 2>&1; then
	"$PYTHON" -m pip install "a @ git+https://github.com/apodgorny/almasi.git"
fi

"$PYTHON" -m pip install -e .

popd > /dev/null

echo
echo "o installed"
echo