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


def comments_to_properties(comments):
    prop_dict = dict()
    for comment in comments:
        prop_def = comment[1:].strip()
        if len(prop_def) == 0:
            continue
        if prop_def[0] in ('!', '#'):
            continue
        punctuation = [prop_def.find(c) for c in ':= '] + [len(prop_def)]
        found = min([pos for pos in punctuation if pos != -1])
        name = prop_def[:found].rstrip()
        value = prop_def[found:].lstrip(":= ").rstrip()
        prop_dict[name] = value
    print [prop_def.find(c) for c in ':= '] + [len(prop_def)]
    return prop_dict


FILES = 'files'
GENE_COLUMN = 'GENE_COLUMN'
DEFAULT_TAG_HEADER = 'DEFAULT_TAG_HEADER'
FILE_DESCRIPTION = 'FILE_DESCRIPTION'
ORGANISM = 'ORGANISM'
GENE_ID_TYPE = 'GENE_ID_TYPE'
DEFAULT_GENES = 'DEFAULT_GENES'


# reads in csv and creates map of lists, where one list contains all headers for gene
# what is key in the map for this list. List value is one string with all values for one header
def read_files():
    print 'started loading csv'
    csv_files = []
    for f in os.listdir(FILES):
        if f.endswith('.csv'):
            csv_files.append(f)

    for csv_file in csv_files:
        with open(FILES + '/' + csv_file, 'rb') as csv_input:
            reader = csv.reader(csv_input, delimiter='\t')
            reading_comments = True
            comments = []
            while reading_comments:
                comment = reader.next()
                if comment[0].startswith("#"):
                    comments.append('\t'.join(comment))
                else:
                    reading_comments = False
            headers_list = comment
            properties = comments_to_properties(comments)
            if GENE_ID_TYPE in properties and ORGANISM in properties and GENE_COLUMN in properties:
                global meta_data
                organism = properties[ORGANISM]
                if organism not in meta_data:
                    meta_data[organism] = {}
                meta_data[organism][csv_file] = {}
                csv_meta_data = meta_data[organism][csv_file]
                csv_meta_data['header_descriptions'] = {}
                gene_map[csv_file] = {}

                if FILE_DESCRIPTION in properties:
                    csv_meta_data[FILE_DESCRIPTION] = properties[FILE_DESCRIPTION]
                else:
                    csv_meta_data[FILE_DESCRIPTION] = csv_file
                    print 'parameter ' + FILE_DESCRIPTION + ' missing for file ' + csv_file
                csv_meta_data[ORGANISM] = properties[ORGANISM]
                csv_meta_data[GENE_ID_TYPE] = properties[GENE_ID_TYPE]
                if DEFAULT_GENES in properties:
                    csv_meta_data[DEFAULT_GENES] = properties[DEFAULT_GENES]
                else:
                    csv_meta_data[DEFAULT_GENES] = ''
                    print 'parameter ' + DEFAULT_GENES + ' missing for file ' + csv_file
                headers_list = map(str.strip, headers_list)
                header_loc = headers_list.index(properties[GENE_COLUMN])
                if DEFAULT_TAG_HEADER in properties:
                    csv_meta_data[DEFAULT_TAG_HEADER] = headers_list.index(properties[DEFAULT_TAG_HEADER])
                else:
                    csv_meta_data[DEFAULT_TAG_HEADER] = 0
                    print 'parameter ' + DEFAULT_TAG_HEADER + ' missing for file ' + csv_file

                del headers_list[header_loc]
                csv_meta_data['headers'] = headers_list

                for header in headers_list:
                    if header in properties:
                        csv_meta_data['header_descriptions'][header] = properties[header]
                    else:
                        csv_meta_data['header_descriptions'][header] = header
                        print 'header "' + header + '" description missing for file ' + csv_file

                for row in reader:
                    row = map(str.strip, row)
                    if len(row) == (len(headers_list) + 1):
                        row_gene = row[header_loc]
                        del row[header_loc]
                        if row_gene not in gene_map[csv_file]:
                            gene_map[csv_file][row_gene] = row
                        else:
                            gene = gene_map[csv_file][row_gene]
                            for i in range(min(len(row), len(headers_list))):
                                gene[i] += '|' + row[i]
                    elif len(row) > 0:
                        print 'headers len: ', len(headers_list), ' row len:', len(row) - 1, ' first row:', row[0]
                print csv_file + ' csv loaded'
            else:
                print ORGANISM + ' or ' + GENE_COLUMN + ' parameter is missing from ' + csv_file

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
    separator = '\t'
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
        self.wfile.write('GENE' + separator + 'TAG' + separator + 'COUNT\r\n')
        for gene in genes_stats:
            for tag in genes_stats[gene]:
                self.wfile.write(gene + separator + tag + separator + str(genes_stats[gene][tag]) + "\r\n")
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
