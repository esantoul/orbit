#!/bin/bash

cd "$( dirname "${BASH_SOURCE[0]}" )"

for i in llvm-common *; do
  if [ -d "$i" ] && [ -f "$i/conanfile.py" ]; then
    echo "Exporting $i..."
    (cd $i && conan export . --user=orbitdeps --channel=stable) || echo "Failed to export $i, continuing..."
  fi
done
