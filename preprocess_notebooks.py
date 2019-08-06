#!/bin/env python
"""
Process a notebook and add swc like styling to the markdown cells.

Usage:
  preprocess_notebooks.py <inputfile> <outputfile>
  preprocess_notebooks.py --version

Options:
  -h --help    Show this help
  --version    Show version.

"""
from textwrap import dedent

import markdown
import nbformat

import nbstripout
import docopt

args = docopt.docopt(__doc__)


formats = {
    "objectives": {"panel_type": "warning",
                   "fa_type": "certificate"},
    "callout": {"panel_type": "warning",
                "fa_type": "thumb-tack"},
    "challenge": {"panel_type": "success",
                  "fa_type": "pencil"},
    "solution": {"panel_type": "primary",
                 "fa_type": "eye"},
    "keypoints": {"panel_type": "success",
                  "fa_type": "exclamation-circle"},
    }
formats["challange"] = formats["challenge"]


def swc_attribution():
    return dedent("""\
    ---
    The material in this notebook is derived from the Software Carpentry lessons
    &copy; [Software Carpentry](http://software-carpentry.org/) under the terms
    of the [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/) license.""")


def tagged_cell(cell):
    tags = bool(len(cell.get("metadata", {}).get("tags", [])))
    md = cell['cell_type'] == 'markdown'
    return tags and md


def post_process(content):
    content = content.replace("<code>", "`")
    content = content.replace("</code>", "`")
    return content


def process_cell_metadata(cell, **kwargs):
    tag = cell['metadata'].get('tags', [])
    if tag:
        tag = tag[0]

    allowed_keys = ["source_hidden", "notebook_only"]
    keys = list(cell.metadata.keys())
    for mkey in keys:
        if mkey not in allowed_keys:
            cell.metadata.pop(mkey)

    return cell


def process_tagged_cell(cell):
    tags = set(cell['metadata'].get('tags', []))
    format_tags = list(tags.intersection(formats.keys()))
    if not format_tags:
        return cell
    elif len(format_tags) > 1:
        print("two or more format tags found, picking one at random")
    tag = list(tags)[0]

    formatter = formats.get(tag, None)
    if not formatter:
        print(f"No formatter found for {tag}")
        return cell

    # Append Prolog
    input_source = formatter.get('prolog', "") + cell['source']

    # Extract the header
    lines = input_source.split("\n")
    title = ""
    title_line = None
    for line in lines:
        if line.startswith("##"):
            title_line = line
            title = line.replace("##", "").strip()
    if title_line:
        lines.remove(title_line)
    input_source = "\n".join(lines)

    # Process Markdown
    content = markdown.markdown(input_source, extensions=["markdown.extensions.codehilite",
                                                          "markdown.extensions.fenced_code"])
    body = dedent("""

    <div class="panel-body">

    {content}

    </div>
    """)
    new_source = dedent("""
    <section class="{tag} panel panel-{panel_type}">
    <div class="panel-heading">
    <h2><span class="fa fa-{fa_type}"></span> {title}</h2>
    </div>
    {body}
    </section>
    """)

    if input_source.strip():
        body = body.format(content=content)
    else:
        body = ""
    # Replace content with formatted version
    cell["source"] = new_source.format(tag=tag, title=title, body=body, **formatter)

    return cell


def process_notebook_metadata(nb):
    nb = strip_kernel_information(nb)
    nb.metadata.pop("celltoolbar", None)
    return nb


def strip_kernel_information(nb):
    default_py_kernel = {
        "name": "python3",
        "display_name": "Python 3",
        "language": "python"
    }
    ks = nb.metadata.get("kernelspec", {})
    if "python" in ks.get('language', "").lower():
        nb.metadata.kernelspec = default_py_kernel
    return nb


def process_cells(nb, **kwargs):
    for ind, cell in enumerate(nb['cells']):
        cell = process_cell(cell, **kwargs)
        cell = process_cell_metadata(cell, **kwargs)

        # Update notebook tree
        nb['cells'][ind] = cell

    if "swc_attribution" in nb.metadata:
        nb['cells'].append(nbformat.v4.new_markdown_cell(swc_attribution()))

    return nb


def strip_cell_input(cell):
    code = cell['cell_type'] == 'code'
    if code and "keep_input" not in cell.metadata.get("tags", []):
        cell["source"] = []
    return cell


def process_cell(cell, strip_input=False):
    # This is some bash kernel sillyness
    outputs = cell.get("outputs", [])
    if len(outputs) >= 2 and "execution_count" in outputs[1].keys():
        cell['outputs'][1].pop("execution_count")

    if tagged_cell(cell):
        cell = process_tagged_cell(cell)

    if strip_input:
        cell = strip_cell_input(cell)

    return cell


def process_notebook(input_file, output_file, strip_input=False):
    nb = nbformat.read(str(input_file), as_version=4)
    nb = process_notebook_metadata(nb)
    nb = process_cells(nb, strip_input=strip_input)
    nb = nbstripout.strip_output(nb, keep_output=False, keep_count=False)
    nbformat.validate(nb)
    nbformat.write(nb, str(output_file))

if __name__ == "__main__":
    process_notebook(args['<inputfile>'], args['<outputfile>'], True)
