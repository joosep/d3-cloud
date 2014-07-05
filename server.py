# !/usr/bin/python
from urlparse import urlparse, parse_qs
from collections import Counter
import SimpleHTTPServer
import SocketServer
import logging
import os
import csv
import sys
import json

meta_data = {}
gene_map = {}


def properties_to_dict(f):
    prop_file = file(f, 'rb')
    prop_dict = dict()
    for prop_line in prop_file:
        prop_def = prop_line.strip()
        if len(prop_def) == 0:
            continue
        if prop_def[0] in ('!', '#'):
            continue
        punctuation = [prop_def.find(c) for c in ':= '] + [len(prop_def)]
        found = min([pos for pos in punctuation if pos != -1])
        name = prop_def[:found].rstrip()
        value = prop_def[found:].lstrip(":= ").rstrip()
        prop_dict[name] = value
    prop_file.close()
    print [prop_def.find(c) for c in ':= '] + [len(prop_def)]
    return prop_dict


FILES = "files"
CSV_FILE = "csv_file"
GENE_COLUMN = 'gene_column'
DEFAULT_HEADER = "default_header"
FILE_DESCRIPTION = "file_description"


# reads in csv and creates map of lists, where one list contains all headers for gene
#what is key in the map for this list. List value is one string with all values for one header
def read_files():
    print 'started loading csv'
    properties_files = []
    for f in os.listdir(FILES):
        if f.endswith('.properties'):
            properties_files.append(f)
    print properties_files
    for properties_file in properties_files:
        properties = properties_to_dict(FILES + '/' + properties_file)
        print properties
        if CSV_FILE in properties and GENE_COLUMN in properties:
            file_tag = os.path.splitext(properties_file)[0]
            with open(FILES + '/' + properties[CSV_FILE], 'rb') as csv_file:

                global meta_data
                meta_data[file_tag] = {}
                meta_data[file_tag]['header_descriptions'] = {}
                gene_map[file_tag] = {}

                if FILE_DESCRIPTION in properties:
                    meta_data[file_tag][FILE_DESCRIPTION] = properties[FILE_DESCRIPTION]
                else:
                    meta_data[file_tag][FILE_DESCRIPTION] = file_tag
                    print 'parameter ' + FILE_DESCRIPTION + ' missing for file ' + properties_file

                reader = csv.reader(csv_file, delimiter='\t')
                headers_list = reader.next()
                headers_list = map(str.strip, headers_list)
                header_loc = headers_list.index(properties[GENE_COLUMN])
                if DEFAULT_HEADER in properties:
                    meta_data[file_tag][DEFAULT_HEADER] = headers_list.index(properties[DEFAULT_HEADER])
                else:
                    meta_data[file_tag][DEFAULT_HEADER] = 0
                    print 'parameter ' + DEFAULT_HEADER + ' missing for file ' + properties_file

                del headers_list[header_loc]
                meta_data[file_tag]['headers'] = headers_list

                for header in headers_list:
                    if header in properties:
                        meta_data[file_tag]['header_descriptions'][header] = properties[header]
                    else:
                        meta_data[file_tag]['header_descriptions'][header] = header
                        print 'header "' + header + '" description missing for file ' + properties_file

                for row in reader:
                    row = map(str.strip, row)
                    if len(row) == (len(headers_list) + 1):
                        row_gene = row[header_loc]
                        del row[header_loc]
                        if row_gene not in gene_map[file_tag]:
                            gene_map[file_tag][row_gene] = row
                        else:
                            gene = gene_map[file_tag][row_gene]
                            for i in range(min(len(row), len(headers_list))):
                                gene[i] += '|' + row[i]
                    elif len(row) > 0:
                        print 'headers len: ', len(headers_list), ' row len:', len(row) - 1, ' first row:', row[0]
                print properties[CSV_FILE] + ' csv loaded'

        else:
            print CSV_FILE + ' or ' + GENE_COLUMN + ' parameter is missing from ' + properties_file

    return


def get_text(self):
    parameters = parse_qs(urlparse(self.path).query)
    if 'file' not in 'header' not in parameters or 'genes' not in parameters:
        print '<H1>Error</H1>'
        error = 'request must have file, header and genes parameters'
        print error
        get_error(self, error)
        return
    header_index = int(parameters['header'][0])
    genes = parameters['genes'][0]
    file = parameters['file'][0]
    gene_list = set(genes.split(' '))
    self.send_response(200)
    self.send_header('Content-type', 'text/html')
    self.end_headers()
    text = ''
    for gene in gene_list:
        if gene in gene_map[file]:
            text += '|' + gene_map[file][gene][header_index]
    self.wfile.write(text)
    return


def get_stats_by_genes(self):
    parameters = parse_qs(urlparse(self.path).query)
    if 'file' not in parameters or 'header' not in parameters or 'genes' not in parameters or 'tag' not in parameters:
        print '<H1>Error</H1>'
        error = 'request must have file, header, genes and tag parameters'
        print error
        get_error(self, error)
        return
    header_index = int(parameters['header'][0])
    genes = parameters['genes'][0]
    tag = parameters['tag'][0]
    file_field = parameters['file'][0]
    gene_list = set(genes.split(' '))
    self.send_response(200)
    self.send_header('Content-type', 'text/html')
    self.end_headers()
    self.wfile.write('count of "' + tag + '" per gene')
    stats = []
    for gene in gene_list:
        if gene in gene_map[file_field]:
            gene_text = gene_map[file_field][gene][header_index].split('|')
            count = gene_text.count(tag)
            if count > 0:
                stats.append({'gene': gene, 'count': count})
    stats = sorted(stats, key=lambda k: k['count'], reverse=True)
    for stat in stats:
        self.wfile.write('\r\n' + stat['gene'] + ': ' + str(stat['count']))
    return


def get_stats_by_all_genes(self, output='json'):
    parameters = parse_qs(urlparse(self.path).query)
    if 'file' not in parameters or 'header' not in parameters or 'genes' not in parameters:
        print '<H1>Error</H1>'
        error = 'request must have file, header, genes and tag parameters'
        print error
        get_error(self, error)
        return
    file_field = parameters['file'][0]
    header_index = int(parameters['header'][0])
    genes = parameters['genes'][0]
    gene_list = set(genes.split(' '))
    genes_stats = {}
    for gene in gene_list:
        if gene in gene_map[file_field]:
            gene_text = gene_map[file_field][gene][header_index].split('|')
            counter = Counter(gene_text)
            genes_stats[gene] = counter
    if output == 'json':
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(genes_stats, sort_keys=True, indent=4))
    elif output == 'csv':
        self.send_response(200)
        self.send_header('Content-type', 'application/csv')
        self.end_headers()
        self.wfile.write('GENE;TAG;COUNT\r\n')
        for gene in genes_stats:
            print gene
            print genes_stats[gene]
            for tag in genes_stats[gene]:
                print tag
                print genes_stats[gene][tag]
                self.wfile.write(gene + ";" + tag + ";" + str(genes_stats[gene][tag]) + "\r\n")
    else:
        print '<H1>Error</H1>'
        error = 'file extension must be \'json\' or \'csv\'.'
        print error
        get_error(self, error)
        return
    return


def get_error(self, error):
    self.send_response(400)
    self.send_header('Content-type', 'text/html')
    self.end_headers()
    self.wfile.write(error)
    return


def get_metadata(self):
    self.send_response(200)
    self.send_header('Content-type', 'application/json')
    self.end_headers()
    self.wfile.write(json.dumps(meta_data, sort_keys=True, indent=4))
    return


class ServerHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/metadata':
            get_metadata(self)
        elif self.path.startswith('/text'):
            get_text(self)
        elif self.path.startswith('/statsbygenes'):
            get_stats_by_genes(self)
        elif self.path.startswith('/statsbyallgenes.json'):
            get_stats_by_all_genes(self, 'json')
        elif self.path.startswith('/statsbyallgenes.csv'):
            get_stats_by_all_genes(self, 'csv')
        else:
            logging.info('GET path: ' + self.path)
            SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)


if __name__ == '__main__':
    if len(sys.argv) > 2:
        PORT = int(sys.argv[2])
        I = sys.argv[1]
    elif len(sys.argv) > 1:
        PORT = int(sys.argv[1])
        I = ''
    else:
        PORT = 8000
        I = ''

    read_files()
    Handler = ServerHandler
    httpd = SocketServer.TCPServer(('', PORT), Handler)
    print 'Serving at: http://%(interface)s:%(port)s' % dict(interface=I or 'localhost', port=PORT)
    httpd.serve_forever()
