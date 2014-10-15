
# Gene Word Cloud

This is a [jasondavies wordcloud](http://www.jasondavies.com/wordcloud/) modified to show different gene data informations as word cloud.
This was made for Bioinformatics course project. 


## Usage

Download the project and run python service: "python server.py".
That will create service at localhost:8000/cloud.html.
It's possible to add some other port when starting server: "python server.py 8080".

New data is added as copy rightly formatted csv (see application help page) into files folder and removed as removing csv from files folder. After changing files, service restart is needed.
