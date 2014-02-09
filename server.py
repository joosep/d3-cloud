#!/usr/bin/python
import SimpleHTTPServer
import SocketServer
import logging
import cgi
import csv
import sys

headers = ""
geneMap = {}
#reads in csv and creates map of lists, where one list contains all headers for gene
#what is key in the map for this list. List value is one string with all values for one header
def readFiles():
    print "started loading csv"
    with open('files/all.csv', 'rb') as csvfile:
        reader = csv.reader(csvfile, delimiter='\t')
        headersList = reader.next()
        geneLoc = headersList.index("Gene")
        del headersList[geneLoc]
        global headers
        headers = '|'.join(headersList);
        for row in reader:
            if len(row) == (len(headersList)+1):
                rowGene = row[geneLoc]
                del row[geneLoc]
                if not geneMap.has_key(rowGene):
                    geneMap[rowGene] = row
                else:
                    gene = geneMap[rowGene]
                    for i in range(min(len(row),len(headersList))):
                            gene[i] += "|" + row[i]
            elif len(row) > 0:
                print "headers len: ",len(headersList)," row len:",len(row)-1," first row:",row[0]
    print "csv loaded"
    return

def getText(self):
    form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD':'POST',
                     'CONTENT_TYPE':self.headers['Content-Type'],
                     })
    if "header" not in form or "genes" not in form:
        print "<H1>Error</H1>"
        print "request must have header and genes parameters"
        return
    header_index=int(form["header"].value)
    genes=form["genes"].value
    geneList = set(genes.split(' '))
    self.send_response(200)
    self.send_header('Content-type', 'text/html')
    self.end_headers()
    text=""
    for gene in geneList:
        if geneMap.has_key(gene):
            text += '|' + geneMap[gene][header_index]
    self.wfile.write(text)
    return

def getHeader(self):
    self.send_response(200)
    self.send_header('Content-type', 'text/html')
    self.end_headers()
    self.wfile.write(headers)
    return

class ServerHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):

    def do_GET(self):
    	if self.path == "/headers" : 
            getHeader(self)
        else:
            logging.warning("GET path: " + self.path)
            SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if self.path == "/text" :
            getText(self)
        else:
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD':'POST',
                         'CONTENT_TYPE':self.headers['Content-Type'],
                         })
            logging.warning("======= POST VALUES =======")
            for item in form.list:
                logging.warning(item)
            logging.warning("POST path: " + self.path)
            SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)

if __name__ == "__main__":
    if len(sys.argv) > 2:
        PORT = int(sys.argv[2])
        I = sys.argv[1]
    elif len(sys.argv) > 1:
        PORT = int(sys.argv[1])
        I = ""
    else:
        PORT = 8000
        I = ""

    readFiles()
    Handler = ServerHandler
    httpd = SocketServer.TCPServer(("", PORT), Handler)
    print "Serving at: http://%(interface)s:%(port)s" % dict(interface=I or "localhost", port=PORT)
    httpd.serve_forever()

