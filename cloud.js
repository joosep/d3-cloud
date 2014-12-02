if(!Object.keys) Object.keys = function(o){
   if (o !== Object(o))
      throw new TypeError('Object.keys called on non-object');
   var ret=[],p;
   for(p in o) if(Object.prototype.hasOwnProperty.call(o,p)) ret.push(p);
   return ret;
}
function transformToAssocArray( prmstr ) {
    var params = {};
    var prmarr = prmstr.split("&");
    for ( var i = 0; i < prmarr.length; i++) {
        var tmparr = prmarr[i].split("=");
        params[tmparr[0]] = tmparr[1];
    }
    return params;
}
function getSearchParameters() {
      var prmstr = decodeURI(window.location.search.substr(1));
      return prmstr != null && prmstr != "" ? transformToAssocArray(prmstr) : {};
}
var fill = d3.scale.category20b();

var w = 960,
    h = 600;

var words = [],
    max,
    scale = 1,
    complete = 0,
    keyword = "",
    tags,
    fontSize,
    scaleValue = "linear",
    spiralValue = "archimedean",
    angleCountValue = "archimedean",
    angleFromValue = "-60",
    angleToValue = "60",
    fontValue = "Impact",
    wordNrValue = "250",
    perlineValue = false,
    maxLength = 30,
    statusText = d3.select("#status"),
    geneNames="HLA-A HLA-B DRD2 CDKN1B NGF NAT2 SAMD3",
    geneFieldValue=geneNames;
    header_fieldValue=0,
    file_fieldValue=0,
    organism_fieldValue=0;

var params = getSearchParameters();

if ( params["organismName"] ) {
organism_fieldValue=params["organismName"];
}
if ( params["fileName"] ) {
file_fieldValue=params["fileName"];
}
if ( params["headerName"] ) {
header_fieldValue=params["headerName"];
}
if ( params["geneValues"] ) {
geneNames=params["geneValues"];
}
if ( params["spiral"] ) {

        spiralValue = params["spiral"];
    if ( spiralValue === "archimedean" ) {
        document.getElementById("archimedean").checked = true;
        document.getElementById("rectangular").checked = false;
    } else {
        document.getElementById("archimedean").checked = false;
        document.getElementById("rectangular").checked = true;
    }
}
if ( params["scale"]) {
     scaleValue = params["scale"];
    if ( scaleValue === document.getElementById("scale-log").value ) {
        document.getElementById("scale-log").checked = true;
        document.getElementById("scale-sqrt").checked = false;
        document.getElementById("scale-linear").checked = false;
    } else if ( scaleValue === document.getElementById("scale-sqrt").value ) {
        document.getElementById("scale-log").checked = false;
        document.getElementById("scale-sqrt").checked = true;
        document.getElementById("scale-linear").checked = false;
    } else {
        document.getElementById("scale-log").checked = false;
        document.getElementById("scale-sqrt").checked = false;
        document.getElementById("scale-linear").checked = true;
    }
}
if ( params["angle-count"] ) {
    angleCountValue=params["angle-count"];
    document.getElementById("angle-count").value = angleCountValue;
}
if ( params["angle-from"] ) {
    angleFromValue=params["angle-from"];
    document.getElementById("angle-from").value = angleFromValue;
}
if ( params["angle-to"] ) {
    angleToValue=params["angle-to"];
    document.getElementById("angle-to").value = angleToValue;
}
if ( params["font"] ) {
    fontValue=params["font"];
    document.getElementById("font").value = fontValue;
}
if ( params["wordNr"] ) {
    wordNrValue=params["wordNr"];
    document.getElementById("max").value = wordNrValue;
}
if ( params["per-line"] ) {
    perlineValue=params["per-line"];
    if (perlineValue === "true") {
        document.getElementById("per-line").checked = true;
   } else {
        document.getElementById("per-line").checked = false;
   }
}
var layout = d3.layout.cloud()
    .timeInterval(10)
    .size([w, h])
    .fontSize(function(d) { return fontSize(+d.value); })
    .text(function(d) { return d.key; })
    .on("word", progress)
    .on("end", draw);

var svg = d3.select("#vis").append("svg")
    .attr("width", w)
    .attr("height", h);

var background = svg.append("g"),
    vis = svg.append("g")
    .attr("transform", "translate(" + [w >> 1, h >> 1] + ")");

d3.select("#download-svg").on("click", downloadSVG);
d3.select("#download-png").on("click", downloadPNG);
d3.select("#download-json").on("click", downloadJSON);
d3.select("#download-csv").on("click", downloadCSV);

d3.select(window).on("hashchange", hashchange);

var header_field = document.getElementById("header_field");
var file_field = document.getElementById("file_field");
var organism_field = document.getElementById("organism_field");

var gene_text_field = document.getElementById("text");
gene_text_field.value=geneNames;

d3.select(window).on("load", hashchange);
var form = d3.select("#form")
    .on("submit", function() {
      load(gene_text_field);
      d3.event.preventDefault();
    });
form.selectAll("input[type=number]")
    .on("click.refresh", function() {
      if (this.value === this.defaultValue) return;
      generate();
      this.defaultValue = this.value;
    });
form.selectAll("input[type=radio], #font")
    .on("change", generate);

function updateVariables(){
   genes = gene_text_field.value.split(d3.select("#per-line").property("checked") ? /\n/g : wordSeparators);
   geneNames=genes;
   geneFieldValue=gene_text_field.value;

   var organism_field_nr = organism_field.selectedIndex;
   if (organism_field_nr == -1) {
    organism_field_nr = 0;
    organism_field.selectedIndex = 0;
   }
   organism_fieldValue=organismKeys[organism_field_nr];

   var file_field_nr = file_field.selectedIndex;
   if (file_field_nr == -1) {
    file_field_nr = 0;
    file_field.selectedIndex=0;
   }
   file_fieldValue=fileKeys[file_field_nr];

   var header_field_nr = header_field.selectedIndex;
   if (header_field_nr == -1) {
    header_fieldValue = metadata[organism_fieldValue][file_fieldValue].DEFAULT_TAG_HEADER;
    header_field.selectedIndex = metadata[organism_fieldValue][file_fieldValue].headers[header_fieldValue]
   } else {
    header_fieldValue = metadata[organism_fieldValue][file_fieldValue].headers[header_field_nr];
   }

   if (document.getElementById("archimedean").checked) {
    spiralValue = document.getElementById("archimedean").value;
   } else {
    spiralValue = document.getElementById("rectangular").value;
   }

   if ( document.getElementById("scale-log").checked ) {
    scaleValue = document.getElementById("scale-log").value;
   } else if ( document.getElementById("scale-sqrt").checked ) {
    scaleValue = document.getElementById("scale-sqrt").value;
   } else {
    scaleValue = document.getElementById("scale-linear").value;
   }
   angleCountValue = document.getElementById("angle-count").value;
   angleFromValue = document.getElementById("angle-from").value;
   angleToValue = document.getElementById("angle-to").value;
   fontValue = document.getElementById("font").value;
   wordNrValue = document.getElementById("max").value;
   perlineValue = d3.select("#per-line").property("checked");
}

wordSeparators = /[\s,\u3031-\u3035\u309b\u309c\u30a0\u30fc\uff70]+/g;
var genes;
var textRequest;
function parseText() {
    if (fileKeys) {
   updateVariables();
   $.ajax({
        type: "GET",
        url: "text?organism="+organism_fieldValue+"&file="+file_fieldValue+"&header="+header_fieldValue+"&genes="+geneNames.join(" ")
     })
    .done(function(data) {
        tags = {};
        var cases = {}
        textRequest = data;
        textRequest.split("\|").forEach(function(word) {
        cases[word.toLowerCase()] = word;
        tags[word = word.toLowerCase()] = (tags[word] || 0) + 1;
        });
        tags = d3.entries(tags).sort(function(a, b) { return b.value - a.value; });
        tags.forEach(function(d) { d.key = cases[d.key]; });
        hideBox();
        generate();
    })
    .fail(function(jqXHR,textStatus,errorThrown){
            if (jqXHR.readyState == 4) {
                resetApplicationOnFail();
            }
    });
  }
}

function generate() {
  layout
      .font(d3.select("#font").property("value"))
      .spiral(d3.select("input[name=spiral]:checked").property("value"));
  fontSize = d3.scale[d3.select("input[name=scale]:checked").property("value")]().range([10, 100]);
  if (tags.length) fontSize.domain([+tags[tags.length - 1].value || 1, +tags[0].value]);
  complete = 0;
  statusText.style("display", null);
  words = [];
  layout.stop().words(tags.slice(0, max = Math.min(tags.length, +d3.select("#max").property("value")))).start();
}

function progress(d) {
  statusText.text(++complete + "/" + max);
}

function copyToClipboard() {
  window.prompt("Copy to clipboard: Ctrl/Cmd+C, Enter", copyData);
}

var copyData = ''
function showBox(e){
     lastClickedTag = e;
     $.ajax({
            type: "GET",
            url: "statsbygenes?organism="+organism_fieldValue+"&file="+file_fieldValue+"&header="+header_fieldValue+"&genes="+geneNames.join(" ")+"&tag="+e.text
         })
     .done(function(data) {
        copyData = data;
        $('.tooltip')[0].innerText = data;
        $('.tooltip').fadeIn().css(({ left:  0, top: 30 }));
        $('.copy_link').fadeIn().css(({left: 0, top: 0 }));
      })
     .fail(function(jqXHR,textStatus,errorThrown){
            if (jqXHR.readyState == 4) {
                resetApplicationOnFail();
           }
        });
}

var lastClickedTag = undefined;
function toggleBox(e){
     if ($('.tooltip').is(":visible") && lastClickedTag.text === e.text) {
        hideBox();
     } else {
     showBox(e)
    }
}
function hideBox(){
    lastClickedTag = undefined;
    $('.tooltip').fadeOut();
    $('.copy_link').fadeOut();
}

function draw(data, bounds) {
  statusText.style("display", "none");
  scale = bounds ? Math.min(
      w / Math.abs(bounds[1].x - w / 2),
      w / Math.abs(bounds[0].x - w / 2),
      h / Math.abs(bounds[1].y - h / 2),
      h / Math.abs(bounds[0].y - h / 2)) / 2 : 1;
  words = data;
  var text = vis.selectAll("text")
      .data(words, function(d) { return d.text.toLowerCase(); });
  text.transition()
      .duration(1000)
      .attr("transform", function(d) { return "translate(" + [d.x, d.y] + ")rotate(" + d.rotate + ")"; })
      .style("font-size", function(d) { return d.size + "px"; });
  text.enter().append("text")
      .attr("text-anchor", "middle")
      .attr("transform", function(d) { return "translate(" + [d.x, d.y] + ")rotate(" + d.rotate + ")"; })
      .style("font-size", function(d) { return d.size + "px"; })
      .on("click", toggleBox)
      .style("opacity", 1e-6)
    .transition()
      .duration(1000)
      .style("opacity", 1);
  text.style("font-family", function(d) { return d.font; })
      .style("fill", function(d) { return fill(d.text.toLowerCase()); })
      .text(function(d) { return d.text; });
  var exitGroup = background.append("g")
      .attr("transform", vis.attr("transform"));
  var exitGroupNode = exitGroup.node();
  text.exit().each(function() {
    exitGroupNode.appendChild(this);
  });
  exitGroup.transition()
      .duration(1000)
      .style("opacity", 1e-6)
      .remove();
  vis.transition()
      .delay(1000)
      .duration(750)
      .attr("transform", "translate(" + [w >> 1, h >> 1] + ")scale(" + scale + ")");
}

// Converts a given word cloud to image/png.
function downloadPNG() {
  var canvas = document.createElement("canvas"),
      c = canvas.getContext("2d");
  canvas.width = w;
  canvas.height = h;
  c.translate(w >> 1, h >> 1);
  c.scale(scale, scale);
  words.forEach(function(word, i) {
    c.save();
    c.translate(word.x, word.y);
    c.rotate(word.rotate * Math.PI / 180);
    c.textAlign = "center";
    c.fillStyle = fill(word.text.toLowerCase());
    c.font = word.size + "px " + word.font;
    c.fillText(word.text, 0, 0);
    c.restore();
  });
  d3.select(this).attr("href", canvas.toDataURL("image/png"));
}

function downloadSVG() {

  d3.select(this).attr("href", "data:image/svg+xml;charset=utf-8;base64," + btoa(unescape(encodeURIComponent(
    svg.attr("version", "1.1")
       .attr("xmlns", "http://www.w3.org/2000/svg")
     .node().parentNode.innerHTML))));
}

function downloadJSON() {
   updateVariables();
   d3.select(this).attr("href","statsbyallgenes.json?organism="+organism_fieldValue+"&file="+file_fieldValue+"&header="+header_fieldValue+"&genes="+geneNames.join(" "))
}

function downloadCSV() {
   updateVariables();
   d3.select(this).attr("href","statsbyallgenes.csv?organism="+organism_fieldValue+"&file="+file_fieldValue+"&header="+header_fieldValue+"&genes="+geneNames.join(" "))
}

function hashchange() {
  load(gene_text_field);
}

function load(f) {
    if (f) parseText();
}

d3.select("#random-palette").on("click", function() {
  paletteJSON("http://www.colourlovers.com/api/palettes/random", {}, function(d) {
    fill.range(d[0].colors);
    vis.selectAll("text")
        .style("fill", function(d) { return fill(d.text.toLowerCase()); });
  });
  d3.event.preventDefault();
});

(function() {
  var r = 40.5,
      px = 35,
      py = 20;

  var angles = d3.select("#angles").append("svg")
      .attr("width", 2 * (r + px))
      .attr("height", r + 1.5 * py)
    .append("g")
      .attr("transform", "translate(" + [r + px, r + py] +")");

  angles.append("path")
      .style("fill", "none")
      .attr("d", ["M", -r, 0, "A", r, r, 0, 0, 1, r, 0].join(" "));

  angles.append("line")
      .attr("x1", -r - 7)
      .attr("x2", r + 7);

  angles.append("line")
      .attr("y2", -r - 7);

  angles.selectAll("text")
      .data([-90, 0, 90])
    .enter().append("text")
      .attr("dy", function(d, i) { return i === 1 ? null : ".3em"; })
      .attr("text-anchor", function(d, i) { return ["end", "middle", "start"][i]; })
      .attr("transform", function(d) {
        d += 90;
        return "rotate(" + d + ")translate(" + -(r + 10) + ")rotate(" + -d + ")translate(2)";
      })
      .text(function(d) { return d + "Â°"; });

  var radians = Math.PI / 180,
      from,
      to,
      count,
      scale = d3.scale.linear(),
      arc = d3.svg.arc()
        .innerRadius(0)
        .outerRadius(r);

  d3.selectAll("#angle-count, #angle-from, #angle-to")
      .on("change", getAngles)
      .on("mouseup", getAngles);

  getAngles();

  function getAngles() {
    count = +d3.select("#angle-count").property("value");
    from = Math.max(-90, Math.min(90, +d3.select("#angle-from").property("value")));
    to = Math.max(-90, Math.min(90, +d3.select("#angle-to").property("value")));
    update();
  }

  function update() {
    scale.domain([0, count - 1]).range([from, to]);
    var step = (to - from) / count;

    var path = angles.selectAll("path.angle")
        .data([{startAngle: from * radians, endAngle: to * radians}]);
    path.enter().insert("path", "circle")
        .attr("class", "angle")
        .style("fill", "#fc0");
    path.attr("d", arc);

    var line = angles.selectAll("line.angle")
        .data(d3.range(count).map(scale));
    line.enter().append("line")
        .attr("class", "angle");
    line.exit().remove();
    line.attr("transform", function(d) { return "rotate(" + (90 + d) + ")"; })
        .attr("x2", function(d, i) { return !i || i === count - 1 ? -r - 5 : -r; });

    var drag = angles.selectAll("path.drag")
        .data([from, to]);
    drag.enter().append("path")
        .attr("class", "drag")
        .attr("d", "M-9.5,0L-3,3.5L-3,-3.5Z")
        .call(d3.behavior.drag()
          .on("drag", function(d, i) {
            d = (i ? to : from) + 90;
            var start = [-r * Math.cos(d * radians), -r * Math.sin(d * radians)],
                m = [d3.event.x, d3.event.y],
                delta = ~~(Math.atan2(cross(start, m), dot(start, m)) / radians);
            d = Math.max(-90, Math.min(90, d + delta - 90)); // remove this for 360Â°
            delta = to - from;
            if (i) {
              to = d;
              if (delta > 360) from += delta - 360;
              else if (delta < 0) from = to;
            } else {
              from = d;
              if (delta > 360) to += 360 - delta;
              else if (delta < 0) to = from;
            }
            update();
          })
          .on("dragend", generate));
    drag.attr("transform", function(d) { return "rotate(" + (d + 90) + ")translate(-" + r + ")"; });
    layout.rotate(function() {
      return scale(~~(Math.random() * count));
    });
    d3.select("#angle-count").property("value", count);
    d3.select("#angle-from").property("value", from);
    d3.select("#angle-to").property("value", to);
  }

  function cross(a, b) { return a[0] * b[1] - a[1] * b[0]; }
  function dot(a, b) { return a[0] * b[0] + a[1] * b[1]; }

});

function updateGeneFormat(geneIdFormat){
    document.getElementById("gene_id_format").innerText=geneIdFormat;
}

function updateFileDescription(file_description,file_uploader){
    document.getElementById("file_description").innerText=file_description+" (uploader: "+file_uploader+")";
}
function updateGenes(genes){
    if (genes) {
        gene_text_field.value=genes
    }
}
processData();
var headers = undefined;
var metadata = undefined;
var headersData = undefined;
var organismKeys = undefined;
var fileKeys = undefined;

function refreshFilesOption(){
          data = metadata[organismKeys[organism_field.selectedIndex]];
          fileKeys= Object.keys(data)
          file_field.innerHTML = "";
          for (var i = 0 ; i < fileKeys.length; i++) {
            var opt = document.createElement("option");
            opt.innerHTML = fileKeys[i];
            opt.value = i;
            opt.title = data[fileKeys[i]].FILE_DESCRIPTION
            file_field.appendChild(opt);
          }
          if (params["fileName"] && fileKeys.indexOf(params["fileName"]) != -1) {
            file_field.selectedIndex = fileKeys.indexOf(params["fileName"]);
          } else {
            file_field.selectedIndex = 0;
          }
          refreshHeadersOption();

          file_field.onchange = refreshHeadersOption;
}
function refreshHeadersOption(){
          data = metadata[organismKeys[organism_field.selectedIndex]][fileKeys[file_field.selectedIndex]];
          updateFileDescription(data.FILE_DESCRIPTION,data.UPLOADER);
          updateGeneFormat(data.GENE_ID_TYPE);
          updateGenes(data.DEFAULT_GENES);
          headers = data.headers;
          header_field.innerHTML = "";
          for (var i = 0 ; i < headers.length; i++) {
            var opt = document.createElement("option");
            opt.innerHTML = headers[i];
            opt.value = i;
            opt.title = data.header_descriptions[headers[i]]
            header_field.appendChild(opt);
          }
          if (params["headerName"] && headers.indexOf(params["headerName"]) != -1) {
            header_field.selectedIndex = headers.indexOf(params["headerName"]);
          } else {
            header_field.selectedIndex = headers.indexOf(data.DEFAULT_TAG_HEADER);
          }
          load(gene_text_field);
          header_field.onchange=hashchange
}

function processData() {
   $.ajax({
        type: "GET",
        url: "metadata",
        dataType: "text"
    })
    .done(function(data) {
        metadata = JSON.parse( data );
        organismKeys = Object.keys(metadata)
        organism_field.innerHTML = "";
        for (var i = 0 ; i < organismKeys.length; i++) {
        var opt = document.createElement("option");
        opt.innerHTML = organismKeys[i];
        opt.value = i;
        opt.title = organismKeys[i];
        organism_field.appendChild(opt);
        }
        if (params["organismName"] && organismKeys.indexOf(params["organismName"]) != -1) {
        organism_field.selectedIndex = organismKeys.indexOf(params["organismName"]);
        } else {
        organism_field.selectedIndex = 0;
        }
        refreshFilesOption();
        organism_field.onchange = refreshFilesOption
    })
    .fail(function(jqXHR,textStatus,errorThrown){
            if (jqXHR.readyState == 4) {
                resetApplicationOnFail();
            }
    });
}

function resetApplicationOnFail() {
    alert("Request failed because service data has been updated. Will reset application");
    processData();
}

function staticUrl() {
    updateVariables();
    url = "/cloud.html?organismName="+organism_fieldValue+"&fileName="+file_fieldValue+"&headerName="+header_fieldValue+
    "&geneValues="+geneFieldValue+"&spiral="+spiralValue+"&scale="+scaleValue+"&angle-count="+
    angleCountValue+"&angle-from="+angleFromValue+"&angle-to="+angleToValue+
    "&font="+fontValue+"&wordNr="+wordNrValue+"&per-line="+perlineValue;
    window.location = encodeURI(url)
}
