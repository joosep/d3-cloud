
# Gene Word Cloud

This is a [jasondavies wordcloud](http://www.jasondavies.com/wordcloud/) modified to show different gene data informations as word cloud.
This was made for Bioinformatics course project. 


## Usage

Download the project and run python service: "python server.py".
That will create service at localhost:8000/cloud.html.
It's possible to add some other port when starting server: "python server.py 8080".

New data withrightly formatted csv/tsv (see application help page) is added when data is  placed into files folder and data is removed when csv/tsv file is removed from files folder. With adding or removing files from files folder, service updates automatically it's content. 


## Needed tools for running application:
python 2.7

python watchdog library (http://pythonhosted.org/watchdog/installation.html)

