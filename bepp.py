import os
import sys
import glob
import argparse
import pandas as pd
import xlrd
from rich.console import Console
from rich_argparse import RichHelpFormatter
from currency_converter import CurrencyConverter

description = """
[bold magenta]Bepp[/bold magenta] helps you deal with CSV and Excel files exported from PayPal and Banca Etica respectively.
"""

def convert_to_eur(date ,amount, currency):
	c = CurrencyConverter(fallback_on_missing_rate=True)
	if currency != 'EUR':
		amount = round(c.convert(amount, currency, 'EUR', date=date), 2)
	return amount

def main():
	parser = argparse.ArgumentParser(
		prog='Bepp',
		description=description,
		formatter_class=RichHelpFormatter
	)
	parser.add_argument('directory', help='Directory containing the source files.')
	parser.add_argument('-m', '--merge', action='store_true', help='Merge the PayPal’s and Banca Etica’s transaction summaries in one unique CSV')
	parser.add_argument('-b', '--backup', action='store_true', help='Save two separate backups containing all the merged original transactions')
	parser.add_argument('-p', '--pp_duplicates', action='store_false', help='Pass this flag to avoid removing PayPal transactions from Banca Etica')
	parser.add_argument('-c', '--convert_to_eur', action='store_true', help='Convert transactions in other currencies to €.\n[bold]NOTE[/bold]: This slows things down very heavily!')
	parser.add_argument('-o', '--output_dir', metavar='OUTPUT', type=str, help='Specify an output directory (the default is the input directory)')
	args = parser.parse_args()

	dir = args.directory
	if not dir.endswith('/'):
		dir = dir + '/'
	output_dir = args.output_dir or dir + 'bepp_export/'
	if not output_dir.endswith('/'):
		output_dir = output_dir + '/'
	os.makedirs(output_dir, exist_ok=True)

	if not os.path.isdir(dir):
		print(f'Error: “{dir}” is not a valid directory.')
		sys.exit(1)

	be_pattern = os.path.join(dir, '*.xls')
	pp_pattern = os.path.join(dir, '*.csv')

	be_files = glob.glob(be_pattern)
	pp_files = glob.glob(pp_pattern)

	if not be_files or not pp_files:
		print('No Excel files (Banca Etica’s export format) or CSV files (PayPal’s export format) found in the specified directory.')
		sys.exit(1)

	be_list = []
	for f in be_files:
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

	if args.pp_duplicates:
		be = be[~be['Descrizione'].str.contains(r'(?i)PayPal', regex=True)]

	be['Descrizione'] = be['Descrizione'].str.replace(r'(?i)(?:.* FAVORE |(Pagamenti|accredito).* A )(?P<who>.*)(?: IND\.ORD\..* Note: | Valuta.*C\/O )(?P<what>.*)(:? ID\..*| CARTA.*)', r'\g<who>, \g<what>', regex=True)
	be['Descrizione'] = be['Descrizione'].str.replace(r'(?i).* FAVORE (?P<who>.*) IND\.ORD\..* Note: (?P<what>.*)', r'\g<who>, \g<what>', regex=True)

	be = be.rename(columns={
		'Valuta' : 'date',
		'Divisa' : 'currency',
		'Descrizione' : 'note'
	})

	if any(be['currency'] != 'EUR') and args.convert_to_eur:
		be['amount'] = be.apply(lambda row: convert_to_eur(row['date'], row['amount'], row['currency']), axis=1)
		be.drop('currency', axis='columns')

	pp_list = []
	for f in pp_files:
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

	if not args.merge:
		be.to_csv(output_dir + 'Banca Etica.csv', index=False, date_format='%Y-%m-%d')
		pp.to_csv(output_dir + 'PayPal.csv', index=False, date_format='%Y-%m-%d')

	all = pd.concat([be, pp], axis=0, ignore_index=True)
	all = all.sort_values(by='date', ascending=False)

	if args.merge:
		all.to_csv(output_dir + 'BEPP.csv', index=False, date_format='%Y-%m-%d')

	if args.backup:
		be_merged.to_csv(output_dir + 'Banca Etica - original.csv', index=False)
		pp_merged.to_csv(output_dir + 'Pay Pal - original.csv', index=False)

if __name__ == '__main__':
	main()
