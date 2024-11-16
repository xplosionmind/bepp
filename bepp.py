import pandas as pd
import xlrd

def main():
	be = pd.DataFrame(pd.read_excel(
		'./private/estrattocontoitalia.xls',
		parse_dates=[1, 2],
		date_format='ISO8601'
	))

	be.pop('Data contabile')

	be.insert(2,'amount', be['Dare'].fillna(be['Avere']))
	be.drop(['Dare', 'Avere', 'Causale'], axis=1, inplace=True)

	be['Descrizione'] = be['Descrizione'].str.replace(r'(?i)(?:.* FAVORE |(Pagamenti|accredito).* A )(?P<who>.*)(?: IND\.ORD\..* Note: | Valuta.*C\/O )(?P<what>.*)(:? ID\..*| CARTA.*)', r'\g<who>, \g<what>', regex=True)
	be['Descrizione'] = be['Descrizione'].str.replace(r'(?i).* FAVORE (?P<who>.*) IND\.ORD\..* Note: (?P<what>.*)', r'\g<who>, \g<what>', regex=True)

	be = be.rename(columns={
		'Valuta' : 'date',
		'Divisa' : 'currency',
		'Descrizione' : 'note'
	})

	print(be)

	pp = pd.DataFrame(pd.read_csv(
		'./private/Download.CSV'
	))

	pp['date'] = pd.to_datetime(pp['Data'], format='%d/%m/%Y')

	pp = pp[['date', 'Nome', 'Lordo', 'Valuta', 'Oggetto', 'Messaggio']]

	pp = pp.dropna(subset=['Nome'])

	pp['Lordo'] = pd.to_numeric(pp['Lordo'].str.replace(',', '.', regex=False))

	pp['Messaggio'] = pp['Nome'] + pp['Messaggio'].apply(lambda msg: f', {msg}' if pd.notna(msg) else '') + pp['Oggetto'].apply(lambda obj: f', {obj}' if pd.notna(obj) else '')
	pp.drop(['Nome', 'Oggetto'], axis=1, inplace=True)

	pp = pp.rename(columns={
		'Lordo' : 'amount',
		'Valuta' : 'currency',
		'Messaggio' : 'note'
	})

	print(pp)

	all = pd.concat([be, pp], axis=0, ignore_index=True)
	all = all.sort_values(by='date')

	print(all)

	all.to_csv('transactions.csv', index=False)

if __name__ == "__main__":
	main()
