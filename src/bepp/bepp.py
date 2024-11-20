import os
import sys
import glob
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdt
from rich import print
from rich_argparse import RichHelpFormatter
from currency_converter import CurrencyConverter

description = '''
[url=https://codeberg.org/tommi/bepp][bold]Bepp[/bold][/url] helps you deal with transaction summary files exported from PayPal and Banca Etica.
'''

epilog = '''
[bold]Note[/bold]: bepp assumes that inside the specified directory all Excel files are Banca Etica’s [italic]estratto conto[/italic] files, and all CSV files are PayPal transaction summaries.
'''

def convert_to_eur(date ,amount, currency):
	c = CurrencyConverter(fallback_on_missing_rate=True)
	if currency != 'EUR':
		amount = round(c.convert(amount, currency, 'EUR', date=date), 2)
	return amount

def main():
	parser = argparse.ArgumentParser(
		prog='Bepp',
		description=description,
		epilog=epilog,
		formatter_class=RichHelpFormatter
	)
	parser.add_argument('directory', metavar='INPUT_DIR', help='Directory containing the source files.')
	parser.add_argument('-b', '--backup', action='store_true', help='Save two separate backups containing all the merged original transactions.')
	parser.add_argument('-c', '--convert_to_eur', action='store_true', help='Convert transactions in other currencies to €.\n[bold]NOTE[/bold]: This slows things down very heavily!')
	parser.add_argument('-d', '--dry_run', action='store_true', help='Run the script without changing or printing anything.')
	parser.add_argument('-m', '--merge', action='store_true', help='Merge the PayPal’s and Banca Etica’s transaction summaries in one unique CSV.')
	parser.add_argument('-n', '--note', action='store_true', help='Only print the note/description.')
	parser.add_argument('-o', '--output_dir', metavar='OUTPUT_DIR', type=str, help='Specify an output directory (default: “bepp_export” subdirectory in the input dir).')
	parser.add_argument('-p', '--keep_pp_dupes', action='store_true', help='Prevent from removing PayPal transactions from Banca Etica.')
	parser.add_argument('-t', '--timeline', action='store_true', help='Plot a timeline graph of the spendings.')
	args = parser.parse_args()

	dir = args.directory
	if not os.path.isdir(dir):
		print(f'[bold red]Error[/bold red]: “{dir}” is not a valid directory.')
		sys.exit(1)

	output_dir = args.output_dir or os.path.join(dir, 'bepp_export')
	if os.path.exists(output_dir):
		if not os.path.isdir(output_dir):
			print(f'[bold red]Error[/bold red]: “{output_dir}” is not a directory.')
			sys.exit(1)
	elif not args.dry_run:
		os.makedirs(output_dir)

	print(f'Reading from {os.path.abspath(dir)}…')

	be_files = glob.glob(os.path.join(dir, '*.xls'))
	be_files.sort()
	pp_files = glob.glob(os.path.join(dir, '*.CSV')) + glob.glob(os.path.join(dir, '*.csv'))
	pp_files.sort()

	if not be_files or not pp_files:
		print('No Excel files (Banca Etica’s export format) or CSV files (PayPal’s export format) found in the specified directory.')
		sys.exit(1)

	print('Banca Etica logs found:')
	be_list = []
	for f in be_files:
		print(f'\t- \'{os.path.basename(f)}\'')
		be_file = pd.DataFrame(pd.read_excel(
			f,
			parse_dates=[1, 2],
			date_format='ISO8601'
		))
		be_list.append(be_file)

	be = be_merged = pd.concat(be_list, ignore_index=True)

	be.insert(2,'amount', be['Dare'].fillna(be['Avere']))
	be = be[['Valuta', 'amount', 'Divisa', 'Descrizione']]
	be = be.sort_values(by='Valuta', ascending=False)

	if not args.keep_pp_dupes:
		be = be[~be['Descrizione'].str.contains(r'(?i)PayPal', regex=True)]

	be_regexs = {
		r'(?i)ADDEBITO BONIFICO .* BANKING (?P<who>.*) Bonifico disposto in.* Cro: \S+ (?P<what>.*)' : r'\g<who>, \g<what>',
		r'(?i)BONIFICO .* FAVORE (?P<who>.*) (?:IND\.ORD|Data [R,A]).* Note: (?P<what>.*) ID\.OPER.*' : r'\g<who>, \g<what>',
		r'(?i)BONIFICO .* FAVORE (?P<who>.*) (?:IND\.ORD|Data [R,A]).* Note: (?P<what>.*)' : r'\g<who>, \g<what>',
		r'(?i)BONIFICO .* FAVORE (.*)' : r'\1',
		r'(?i)Pagamenti paesi .* A (?P<who>.*) Valuta .* C\/O (?P<what>.*) CARTA N\..*' : r'\g<who>, \g<what>',
		r'(?i)Prelievi paesi .* A (?P<who>.*) Valuta .* C\/O (?P<what>.*) CARTA N\..*' : r'PRELIEVO: \g<who>, \g<what>',
		r'(?i)ACCREDITO VISA .* A (?P<who>.*) Valuta .* C\/O (?P<what>.*) CARTA N\..*' : r'\g<who>, \g<what>',
		r'(?i)ADDEBITO DIRETTO CORE \S+ Prg\.Car\...\S+ \S+ (.*)' : r'\1',
		r'(?i)PAGAMENTO NEXI.*Presso: (.*)' : r'\1',
		r'(?i)SUMUP \*(.*)' : r'\1',
		r'(?i)PAGAMENTI DIVERSI (.*)' : r'\1'
	}

	for pattern, replacement in be_regexs.items():
		be['Descrizione'] = be['Descrizione'].str.replace(pattern, replacement, regex=True)

	be = be.rename(columns={
		'Valuta' : 'date',
		'Divisa' : 'currency',
		'Descrizione' : 'note'
	})

	if any(be['currency'] != 'EUR') and args.convert_to_eur:
		be['amount'] = pd.to_numeric(be.apply(lambda row: convert_to_eur(row['date'], row['amount'], row['currency']), axis=1))
		be.drop('currency', axis='columns')

	print('PayPal logs found:')
	pp_list = []
	for f in pp_files:
		print(f'\t- \'{os.path.basename(f)}\'')
		pp_file = pd.DataFrame(pd.read_csv(f))
		pp_file = pp_file.dropna(axis='columns', how='all')
		pp_list.append(pp_file)

	pp = pp_merged = pd.concat(pp_list, ignore_index=True)

	pp['date'] = pd.to_datetime(pp['Data'], format='%d/%m/%Y')
	pp = pp.sort_values(by='date', ascending=False)

	pp = pp[['date', 'Nome', 'Lordo', 'Valuta', 'Oggetto', 'Messaggio']]
	pp = pp.dropna(subset=['Nome'])

	pp['Lordo'] = pd.to_numeric(pp['Lordo'].str.replace('.', '', regex=False).str.replace(',', '.', regex=False))

	pp['Messaggio'] = pp['Nome'] + pp['Messaggio'].apply(lambda msg: f', {msg}' if pd.notna(msg) else '') + pp['Oggetto'].apply(lambda obj: f', {obj}' if pd.notna(obj) else '')
	pp.drop(['Nome', 'Oggetto'], axis='columns', inplace=True)

	pp = pp.rename(columns={
		'Lordo' : 'amount',
		'Valuta' : 'currency',
		'Messaggio' : 'note'
	})

	if any(pp['currency'] != 'EUR') and args.convert_to_eur:
		pp['amount'] = pp.apply(lambda row: convert_to_eur(row['date'], row['amount'], row['currency']), axis=1)
		pp.drop('currency', axis='columns')

	if not args.merge and not args.dry_run:
		be.to_csv(os.path.join(output_dir, 'Banca Etica.csv'), index=False, date_format='%Y-%m-%d')
		pp.to_csv(os.path.join(output_dir, 'PayPal.csv'), index=False, date_format='%Y-%m-%d')
		print(f'[bold green]Success![/bold green] Files exported in {os.path.abspath(output_dir)}')

	all = pd.concat([be, pp], axis=0, ignore_index=True)
	all['amount'] = pd.to_numeric(all['amount'])
	all = all.sort_values(by='date', ascending=False)

	if args.merge and not args.dry_run:
		if args.note:
			all = all['note']
		all.to_csv(os.path.join(output_dir, 'Bepp.csv'), index=False, date_format='%Y-%m-%d')
		print(f'[bold green]Success![/bold green] “Bepp.csv” exported in {os.path.abspath(output_dir)}')

	if args.backup and not args.dry_run:
		be_merged.to_csv(os.path.join(output_dir, 'Banca Etica - original.csv'), index=False)
		pp_merged.to_csv(os.path.join(output_dir, 'Pay Pal - original.csv'), index=False)
		print(f'[italic]Backup files exported in {os.path.abspath(output_dir)}[/italic]')

	if args.dry_run:
		print(all)
		all.info()

	if args.timeline:
		income_all = all[all['amount'] > 0]
		expenses_all = all[all['amount'] < 0]
		plt.figure()
		plt.scatter(income_all['date'], income_all['amount'], color='green', label='Income', alpha=0.5)
		plt.scatter(expenses_all['date'], expenses_all['amount'], color='red', label='Expenses', alpha=0.5)
		plt.plot(all['date'], all['amount'].cumsum(), 'b-', label='Cash flow')
		plt.title('Cash Flow Over Time')
		plt.xlabel('Date')
		plt.ylabel('Amount')
		#plt.grid(True)
		plt.legend()
		plt.gca().xaxis.set_major_formatter(mdt.DateFormatter('%Y-%m-%d'))
		plt.gcf().autofmt_xdate()
		plt.tight_layout()
		plt.show()

if __name__ == '__main__':
	main()
