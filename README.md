<div align='center'>
	<h1>🏦 Bepp 🧮</h1>
	<p>A tiny tool to manage, clean, and merge transaction exports from <a href='https://bancaetica.it'>Banca Etica</a> and <a href='https://paypal.com'>PayPal</a>.</p>
	<img alt='PyPI, Status – Shields.io badge' src='https://img.shields.io/pypi/status/bepp?style=flat'>
	<img alt='PyPI, Version – Shields.io badge' src='https://img.shields.io/pypi/v/bepp?style=flat&logo=pypi'>
	<img alt='PyPI, Python Version – Shields.io badge' src='https://img.shields.io/pypi/pyversions/bepp?style=flat&logo=python'>
	<img alt='PyPI, License – Shields.io badge' src='https://img.shields.io/pypi/l/bepp?style=flat'>
</div>

## ℹ️ About

I wrote this script to learn and practice with Python and [pandas](https://pandas.pydata.org/), while also getting something I really needed out of it.

## ⏬ Install

1. [Install uv](https://docs.astral.sh/uv/getting-started/installation/ 'Installing uv')
2. [Start a virtual environment](https://docs.astral.sh/uv/pip/environments/ 'Python environments – uv documentation'): `uv venv`
2. Install the package: `uv pip install bepp`
	- append `-U` to install at the user level
	- append `--system` to install system-wide

## 📊 Usage

| argument | type | default | description |
|---|---|---|---|
| **`input/path/`** | string | **Required** | Input directory, containing the source CSV and Excel files. |
| `-b`, `--backup` | boolean | False | Save one CSV backup per kind containing all the original transactions, with no modification. |
| `-c`, `--convert_to_eur` | boolean | False | Convert transactions in other currencies to €. **Note**: This *heavily* slows down the process! |
| `-d`, `--dry_run` | boolean | False | Run the script without changing or printing anything. |
| `-m`, `--merge` | boolean | False | Merge the PayPal’s and Banca Etica’s transaction summaries in one unique CSV. |
| `-n`, `--note` | boolean | False | Only print the note/description (useful for debugging description regexs). |
| `-o`, `--output_dir` | string | `input/path/`<br>+<br>`bepp_export/` | Specify an output directory. |
| `-p`, `--keep_pp_dupes` | boolean | False | Prevent from removing PayPal transactions in Banca Etica’s logs. |
| `-t`, `--timeline` | boolean | False | Plot a timeline graph of the spendings. |

**Note**: Bepp assumes that inside the specified directory all Excel files are Banca Etica’s “estratto conto” files, and all CSV files are PayPal transaction summaries.

## ♻️ License

Everything inside this repository is licensed under the [GNU Affero General Public License, version 3](https://www.gnu.org/licenses/agpl-3.0.txt).
