pushd "$(dirname "$0")" > /dev/null

py -m pip uninstall -y o
py -m pip install -e ../almasi
py -m pip install -e .

popd > /dev/null
