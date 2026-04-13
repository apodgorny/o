import os
import time
import tempfile


N = 10_000


def format_seconds(value):
	text = ''

	if value < 1e-6:
		text = f'{value * 1e9:.3f}ns'
	elif value < 1e-3:
		text = f'{value * 1e6:.3f}µs'
	elif value < 1:
		text = f'{value * 1e3:.3f}ms'
	else:
		text = f'{value:.6f}s'

	return text


def measure_write_once(path):
	data  = b'x' * N
	start = time.perf_counter()

	with open(path, 'wb', buffering=0) as f:
		f.write(data)

	end = time.perf_counter()
	return end - start


def measure_read_once(path):
	start = time.perf_counter()

	with open(path, 'rb', buffering=0) as f:
		f.read(N)

	end = time.perf_counter()
	return end - start


def measure_write_many(path):
	start = time.perf_counter()

	with open(path, 'wb', buffering=0) as f:
		for i in range(N):
			f.seek(i)
			f.write(b'x')

	end = time.perf_counter()
	return end - start


def measure_read_many(path):
	start = time.perf_counter()

	with open(path, 'rb', buffering=0) as f:
			for i in range(N):
				f.seek(i)
				f.read(1)

	end = time.perf_counter()
	return end - start


def print_intro():
	print('Podgorny aggregation benefit demo')
	print('=' * 80)
	print()
	print(f'N = {N}')
	print()
	print('We compare two ways to move the same total amount of data:')
	print()
	print('1. Aggregated act')
	print('   - write N bytes once')
	print('   - read  N bytes once')
	print()
	print('2. Fragmented act ("ushatka")')
	print('   - write 1 byte N times with seek')
	print('   - read  1 byte N times with seek')
	print()
	print('The ratio many / one is the aggregation benefit coefficient.')
	print('The larger it is, the more the system rewards aggregation.')
	print()


def print_write_report(one_w, many_w):
	ratio         = many_w / one_w
	inverse_ratio = one_w / many_w
	normalized    = 1 - inverse_ratio

	print('WRITE')
	print('-' * 80)
	print(f'one_w              = {format_seconds(one_w)}')
	print(f'many_w             = {format_seconds(many_w)}')
	print(f'aggregation benefit= {ratio:.3f}x')
	print(f'inverse ratio      = {inverse_ratio:.6f}')
	print(f'normalized benefit = {normalized:.6f}')
	print()
	print('Meaning:')
	print(f'- aggregated write is about {ratio:.3f} times cheaper than fragmented write')
	print(f'- one big write costs about {inverse_ratio:.6f} of the ushatka write')
	print(f'- normalized benefit is {normalized:.6f} on a 0..1 scale')
	print()


def print_read_report(one_r, many_r):
	ratio         = many_r / one_r
	inverse_ratio = one_r / many_r
	normalized    = 1 - inverse_ratio

	print('READ')
	print('-' * 80)
	print(f'one_r              = {format_seconds(one_r)}')
	print(f'many_r             = {format_seconds(many_r)}')
	print(f'aggregation benefit= {ratio:.3f}x')
	print(f'inverse ratio      = {inverse_ratio:.6f}')
	print(f'normalized benefit = {normalized:.6f}')
	print()
	print('Meaning:')
	print(f'- aggregated read is about {ratio:.3f} times cheaper than fragmented read')
	print(f'- one big read costs about {inverse_ratio:.6f} of the ushatka read')
	print(f'- normalized benefit is {normalized:.6f} on a 0..1 scale')
	print()


def print_conclusion(one_w, many_w, one_r, many_r):
	write_ratio = many_w / one_w
	read_ratio  = many_r / one_r

	print('CONCLUSION')
	print('-' * 80)
	print('Aggregation benefit coefficient:')
	print(f'- write: {write_ratio:.3f}x')
	print(f'- read : {read_ratio:.3f}x')
	print()
	print('Interpretation:')
	print('- near 1x  -> aggregation gives little benefit')
	print('- high     -> aggregation is strongly rewarded')
	print('- very high-> the system dislikes fragmented I/O and prefers doing it all at once')
	print()


def main():
	print_intro()

	with tempfile.TemporaryDirectory() as tmp:
		path = os.path.join(tmp, 'podgorny_equilibrium.bin')

		one_w  = measure_write_once(path)
		one_r  = measure_read_once(path)
		many_w = measure_write_many(path)
		many_r = measure_read_many(path)

		print_write_report(one_w, many_w)
		print_read_report(one_r, many_r)
		print_conclusion(one_w, many_w, one_r, many_r)


if __name__ == '__main__':
	main()