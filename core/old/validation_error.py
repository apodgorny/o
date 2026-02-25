from pydantic import ValidationError

def humanize(self):
	lines = [f'In `{ValidationError.last_model}`']
	for e in self.errors():
		var = '.'.join(str(x) for x in e.get('loc', [])) or 'unknown'
		t1  = e.get('type', 'unknown')
		v1  = e.get('input', 'unknown')
		t2  = type(v1).__name__ if v1 != 'unknown' else 'unknown'
		v1  = str(v1)
		if len(v1) > 300:
			v1 = v1[:300] + ' ...'
		if t1 == 'missing':
			line = f'  - `{var}`: is missing'
		elif t1 == 'extra_forbidden':
			line = f'  - `{var}`: is unexpected'
		else:
			line = f'  - `{var}`: expected `{t1}`, got `{t2}({v1})`'
		lines.append(line)
	return '\n'.join(lines)

def validationerror_str(self):
	return self.humanize()

ValidationError.humanize = humanize
ValidationError.__str__  = validationerror_str
ValidationError.__repr__ = validationerror_str