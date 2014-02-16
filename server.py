#!/usr/bin/python
from urlparse import urlparse, parse_qs
from collections import Counter
import SimpleHTTPServer
import SocketServer
import logging
import cgi
import csv
import sys
import json

headers = ''
gene_map = {}


#reads in csv and creates map of lists, where one list contains all headers for gene
#what is key in the map for this list. List value is one string with all values for one header
def read_files():
    print 'started loading csv'
    with open('files/all.csv', 'rb') as csvfile:
        reader = csv.reader(csvfile, delimiter='\t')
        headers_list = reader.next()
        header_loc = headers_list.index('Gene')
        del headers_list[header_loc]
        global headers
        headers = '|'.join(headers_list)
        for row in reader:
            if len(row) == (len(headers_list) + 1):
                row_gene = row[header_loc]
                del row[header_loc]
                if row_gene not in gene_map:
                    gene_map[row_gene] = row
                else:
                    gene = gene_map[row_gene]
                    for i in range(min(len(row), len(headers_list))):
                        gene[i] += '|' + row[i]
            elif len(row) > 0:
                print 'headers len: ', len(headers_list), ' row len:', len(row) - 1, ' first row:', row[0]
    print 'csv loaded'
    return


def get_text(self):
    parameters = parse_qs(urlparse(self.path).query)
    if 'header' not in parameters or 'genes' not in parameters:
        print '<H1>Error</H1>'
        print 'request must have header and genes parameters'
        return
    header_index = int(parameters['header'][0])
    genes = parameters['genes'][0]
    gene_list = set(genes.split(' '))
    self.send_response(200)
    self.send_header('Content-type', 'text/html')
    self.end_headers()
    text = ''
    for gene in gene_list:
        if gene in gene_map:
            text += '|' + gene_map[gene][header_index]
    self.wfile.write(text)
    return


def get_stats_by_genes(self):
    parameters = parse_qs(urlparse(self.path).query)
    if 'header' not in parameters or 'genes' not in parameters or 'tag' not in parameters:
        print '<H1>Error</H1>'
        print 'request must have header, genes and tag parameters'
        return
    header_index = int(parameters['header'][0])
    genes = parameters['genes'][0]
    tag = parameters['tag'][0]
    gene_list = set(genes.split(' '))
    self.send_response(200)
    self.send_header('Content-type', 'text/html')
    self.end_headers()
    self.wfile.write('count of "' + tag + '" per gene')
    for gene in gene_list:
        if gene in gene_map:
            gene_text = gene_map[gene][header_index].split('|')
            count = gene_text.count(tag)
            if count > 0:
                self.wfile.write('\r\n' + gene + ': ' + str(count))
    return


def get_stats_by_all_genes(self):
    parameters = parse_qs(urlparse(self.path).query)
    if 'header' not in parameters or 'genes' not in parameters:
        print '<H1>Error</H1>'
        print 'request must have header, genes and tag parameters'
        return
    header_index = int(parameters['header'][0])
    genes = parameters['genes'][0]
    gene_list = set(genes.split(' '))
    self.send_response(200)
    self.send_header('Content-type', 'application/json')
    self.end_headers()
    genes_stats = {}
    for gene in gene_list:
        if gene in gene_map:
            gene_text = gene_map[gene][header_index].split('|')
            counter = Counter(gene_text)
            genes_stats[gene] = counter
    self.wfile.write(json.dumps(genes_stats, sort_keys=True, indent=4))
    return


def get_header(self):
    self.send_response(200)
    self.send_header('Content-type', 'text/html')
    self.end_headers()
    self.wfile.write(headers)
    return


class ServerHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/headers':
            get_header(self)
        elif self.path.startswith('/text'):
            get_text(self)
        elif self.path.startswith('/statsbygenes'):
            get_stats_by_genes(self)
        elif self.path.startswith('/statsbyallgenes'):
            get_stats_by_all_genes(self)
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
