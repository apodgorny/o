pushd "$(dirname "$0")" > /dev/null

files=$(
	find . -type f -name '*.py' \
		! -path './root/tests/*' \
		! -path './.git/*' \
		! -path './*/__pycache__/*' \
		| sort
)

file_count=0
line_count=0

if [ -n "$files" ]; then
	file_count=$(printf '%s\n' "$files" | wc -l | awk '{print $1}')
	line_count=$(printf '%s\n' "$files" | xargs wc -l | tail -n 1 | awk '{print $1}')
fi

printf '-----------------------------\n'
printf 'Codebase size:\n'
printf '-----------------------------\n'
printf 'Python files: %s\n' "$file_count"
printf 'Python lines: %s\n' "$line_count"
printf '-----------------------------\n'

popd > /dev/null
