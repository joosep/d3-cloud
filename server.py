# !/usr/bin/python
from urlparse import urlparse, parse_qs
from multiprocessing import Manager, Lock
from collections import Counter
import SimpleHTTPServer
import SocketServer
import logging
import os
import csv
import sys
import json
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

gene_map = {}
meta_data = {}

file_to_organism_map = {}

FILES = 'files'
GENE_COLUMN = 'GENE_COLUMN'
DEFAULT_TAG_HEADER = 'DEFAULT_TAG_HEADER'
FILE_DESCRIPTION = 'FILE_DESCRIPTION'
ORGANISM = 'ORGANISM'
GENE_ID_TYPE = 'GENE_ID_TYPE'
DEFAULT_GENES = 'DEFAULT_GENES'

HEADERS = 'headers'
HEADERS_DESCRIPTIONS = 'header_descriptions'

resource_lock = Lock()


def main():
    global gene_map, meta_data, file_to_organism_map
    interface, port = get_interface_port_from_arguments()
    manager = Manager()
    gene_map = manager.dict()
    meta_data = manager.dict()
    file_to_organism_map = manager.dict()
    read_files()
    directory_observer = start_observing_files()
    serve_application(interface, port)
    directory_observer.stop()
    directory_observer.join()


def serve_application(interface, port):
    handler = ServerHandler
    httpd = SocketServer.TCPServer((interface, port), handler)
    print 'Serving at: http://%(interface)s:%(port)s' % dict(interface=interface or 'localhost', port=port)
    httpd.serve_forever()


def get_file_name(file_path):
    file_name = file_path[file_path.rfind('/') + 1:]
    return file_name


def delete_file_data(file_path):
    file_name = get_file_name(file_path)
    resource_lock.acquire()
    try:
        organism = file_to_organism_map[file_name]
        del gene_map[file_name]
        del meta_data[organism][file_name]
    except KeyError as e:
        print "Tried to delete", file_name, "when got error: ", e
    finally:
        resource_lock.release()


def add_file_data(file_path):
    file_name = get_file_name(file_path)
    add_csv_file_to_maps(file_name)


def change_file_data_name(src_path, dest_path):
    src_file = get_file_name(src_path)
    dest_file = get_file_name(dest_path)
    resource_lock.acquire()
    try:
        gene_map[dest_file] = gene_map.pop(src_file)
        organism = file_to_organism_map[src_file]
        meta_data[organism][dest_file] = meta_data[organism].pop(src_file)
        file_to_organism_map[dest_file] = organism
    except KeyError as e:
        print "Tried to change", src_path, "file name to ", dest_path, "when got error: ", e
    finally:
        resource_lock.release()


class InputFilesHandler(PatternMatchingEventHandler):
    def on_modified(self, event):
        file_name = event.src_path
        delete_file_data(file_name)
        add_file_data(file_name)

    def on_deleted(self, event):
        delete_file_data(event.src_path)

    def on_created(self, event):
        add_file_data(event.src_path)

    def on_moved(self, event):
        change_file_data_name(event.src_path, event.dest_path)


def start_observing_files():
    event_handler = InputFilesHandler(patterns=['*.csv', '*.tsv'], ignore_directories=True)
    dir_observer = Observer()
    dir_observer.schedule(event_handler, path=FILES, recursive=False)
    dir_observer.start()
    return dir_observer


# reads in csv and creates map of lists, where one list contains all headers for gene
# what is key in the map for this list. List value is one string with all values for one header
def read_files():
    print 'started loading csv'
    csv_files = []
    for f in os.listdir(FILES):
        if f.endswith('.csv') or f.endswith('.tsv'):
            csv_files.append(f)
    for csv_file in csv_files:
        add_csv_file_to_maps(csv_file)
    return


def add_csv_file_to_maps(csv_file):
    global gene_map
    global meta_data
    global file_to_organism_map
    try:
        file_gene_map, file_meta_data, organism = get_gene_and_meta_data(csv_file)
        resource_lock.acquire()
        try:
            file_to_organism_map[csv_file] = organism
            if file_gene_map is not {}:
                gene_map[csv_file] = file_gene_map
                if organism in meta_data:
                    meta_data[organism][csv_file] = file_meta_data
                else:
                    meta_data[organism] = {csv_file: file_meta_data}
        finally:
            resource_lock.release()
    except Exception as e:
        print "ERROR when reading file ", csv_file, ":", e


def get_gene_and_meta_data(csv_file):
    file_gene_map = {}
    file_meta_data = {}
    organism = None
    with open(FILES + '/' + csv_file, 'rb') as csv_input:
        print "starts loading file ", csv_file
        reader = csv.reader(csv_input, delimiter='\t')
        comments, headers = get_comments_and_headers(reader)
        properties = comments_to_properties(comments)
        organism = properties[ORGANISM]
        if has_required_properties(properties):
            headers_list, header_loc = get_header_list_and_loc(headers, properties)
            file_meta_data = gen_csv_metadata(csv_file, headers_list, properties)
            file_gene_map = gen_file_gene_map(reader, headers_list, header_loc)
            print csv_file + ' csv loaded'
        else:
            print ORGANISM + ' or ' + GENE_COLUMN + ' parameter is missing from ' + csv_file
    return file_gene_map, file_meta_data, organism


def get_comments_and_headers(reader):
    reading_comments = True
    comments = []
    while reading_comments:
        comment = reader.next()
        if comment[0].startswith("#"):
            comments.append('\t'.join(comment))
        else:
            reading_comments = False
    return comments, comment


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
    return prop_dict


def has_required_properties(properties):
    return GENE_ID_TYPE in properties and ORGANISM in properties and GENE_COLUMN in properties


def get_header_list_and_loc(headers, properties):
    headers_list = map(str.strip, headers)
    header_loc = headers_list.index(properties[GENE_COLUMN])
    del headers_list[header_loc]
    return headers_list, header_loc


def gen_csv_metadata(csv_file, headers_list, properties):
    csv_meta_data = {ORGANISM: properties[ORGANISM], GENE_ID_TYPE: properties[GENE_ID_TYPE], HEADERS: headers_list,
                     HEADERS_DESCRIPTIONS: {}}
    if FILE_DESCRIPTION in properties:
        csv_meta_data[FILE_DESCRIPTION] = properties[FILE_DESCRIPTION]
    else:
        csv_meta_data[FILE_DESCRIPTION] = csv_file
        print 'parameter ' + FILE_DESCRIPTION + ' missing for file ' + csv_file
    if DEFAULT_GENES in properties:
        csv_meta_data[DEFAULT_GENES] = properties[DEFAULT_GENES]
    else:
        csv_meta_data[DEFAULT_GENES] = ''
        print 'parameter ' + DEFAULT_GENES + ' missing for file ' + csv_file
    if DEFAULT_TAG_HEADER in properties:
        csv_meta_data[DEFAULT_TAG_HEADER] = headers_list.index(properties[DEFAULT_TAG_HEADER])
    else:
        csv_meta_data[DEFAULT_TAG_HEADER] = 0
        print 'parameter ' + DEFAULT_TAG_HEADER + ' missing for file ' + csv_file
    for header in headers_list:
        if header in properties:
            csv_meta_data[HEADERS_DESCRIPTIONS][header] = properties[header]
        else:
            csv_meta_data[HEADERS_DESCRIPTIONS][header] = header
            print 'header "' + header + '" description missing for file ' + csv_file
    return csv_meta_data


def gen_file_gene_map(reader, headers_list, header_loc):
    file_gene_map = {}
    for row in reader:
        row = map(str.strip, row)
        if len(row) == (len(headers_list) + 1):
            row_gene = row[header_loc]
            del row[header_loc]
            if row_gene not in file_gene_map:
                file_gene_map[row_gene] = row
            else:
                gene = file_gene_map[row_gene]
                for i in range(min(len(row), len(headers_list))):
                    gene[i] += '|' + row[i]
        elif len(row) > 0:
            print 'headers len: ', len(headers_list), ' row len:', len(row) - 1, ' first row:', row[0]
    return file_gene_map


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
    write_html_headers(self)
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
    write_html_headers(self)
    self.wfile.write('count of "' + tag + '" per gene')
    stats = []
    stats = generate_stat_list(file_field, gene_list, header_index, stats, tag)
    for stat in stats:
        self.wfile.write('\r\n' + stat['gene'] + ': ' + str(stat['count']))
    return


def generate_stat_list(file_field, gene_list, header_index, stats, tag):
    for gene in gene_list:
        if gene in gene_map[file_field]:
            gene_text = gene_map[file_field][gene][header_index].split('|')
            count = gene_text.count(tag)
            if count > 0:
                stats.append({'gene': gene, 'count': count})
    stats = sorted(stats, key=lambda k: k['count'], reverse=True)
    return stats


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
        write_json_headers(self)
        self.wfile.write(json.dumps(genes_stats, sort_keys=True, indent=4))
    elif output == 'csv':
        write_csv_headers(self)
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
    write_json_headers(self)
    self.wfile.write(json.dumps(dict(meta_data)))
    return


def write_html_headers(self):
    self.send_response(200)
    self.send_header('Content-type', 'text/html')
    self.end_headers()


def write_json_headers(self):
    self.send_response(200)
    self.send_header('Content-type', 'application/json')
    self.end_headers()


def write_csv_headers(self):
    self.send_response(200)
    self.send_header('Content-type', 'application/csv')
    self.end_headers()


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


def get_interface_port_from_arguments():
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
        interface = sys.argv[1]
    elif len(sys.argv) > 1:
        port = int(sys.argv[1])
        interface = ''
    else:
        port = 8000
        interface = ''
    return interface, port


if __name__ == '__main__':
    main()
