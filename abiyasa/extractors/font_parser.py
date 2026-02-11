import json
import sys
from io import BytesIO
from pathlib import Path

import fitz
from fontTools.cffLib import CFFFontSet
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

STANDARD_ENCODING_UNICODE = {
    'space': 0x0020, 'exclam': 0x0021, 'quotedbl': 0x0022, 'numbersign': 0x0023,
    'dollar': 0x0024, 'percent': 0x0025, 'ampersand': 0x0026, 'quoteright': 0x2019,
    'parenleft': 0x0028, 'parenright': 0x0029, 'asterisk': 0x002A, 'plus': 0x002B,
    'comma': 0x002C, 'hyphen': 0x002D, 'period': 0x002E, 'slash': 0x002F,
    'zero': 0x0030, 'one': 0x0031, 'two': 0x0032, 'three': 0x0033, 'four': 0x0034,
    'five': 0x0035, 'six': 0x0036, 'seven': 0x0037, 'eight': 0x0038, 'nine': 0x0039,
    'colon': 0x003A, 'semicolon': 0x003B, 'less': 0x003C, 'equal': 0x003D,
    'greater': 0x003E, 'question': 0x003F, 'at': 0x0040,
    'A': 0x0041, 'B': 0x0042, 'C': 0x0043, 'D': 0x0044, 'E': 0x0045, 'F': 0x0046,
    'G': 0x0047, 'H': 0x0048, 'I': 0x0049, 'J': 0x004A, 'K': 0x004B, 'L': 0x004C,
    'M': 0x004D, 'N': 0x004E, 'O': 0x004F, 'P': 0x0050, 'Q': 0x0051, 'R': 0x0052,
    'S': 0x0053, 'T': 0x0054, 'U': 0x0055, 'V': 0x0056, 'W': 0x0057, 'X': 0x0058,
    'Y': 0x0059, 'Z': 0x005A,
    'bracketleft': 0x005B, 'backslash': 0x005C, 'bracketright': 0x005D,
    'asciicircum': 0x005E, 'underscore': 0x005F, 'quoteleft': 0x2018,
    'a': 0x0061, 'b': 0x0062, 'c': 0x0063, 'd': 0x0064, 'e': 0x0065, 'f': 0x0066,
    'g': 0x0067, 'h': 0x0068, 'i': 0x0069, 'j': 0x006A, 'k': 0x006B, 'l': 0x006C,
    'm': 0x006D, 'n': 0x006E, 'o': 0x006F, 'p': 0x0070, 'q': 0x0071, 'r': 0x0072,
    's': 0x0073, 't': 0x0074, 'u': 0x0075, 'v': 0x0076, 'w': 0x0077, 'x': 0x0078,
    'y': 0x0079, 'z': 0x007A,
    'braceleft': 0x007B, 'bar': 0x007C, 'braceright': 0x007D, 'asciitilde': 0x007E,
    '.notdef': None,
}

def export_to_json(glyphs, output_path):
    """Export glyph data to JSON file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(glyphs, f, indent=2, ensure_ascii=False)
    #print(f"Exported to JSON in {output_path}")


def extract_unicode_mappings(font):
    """Extract Unicode mappings from font."""
    unicode_map = {}

    try:
        cmap = font.getBestCmap()
        if cmap:
            unicode_map = {v: k for k, v in cmap.items()}
            return unicode_map
    except:
        pass

    try:
        cmap_table = font['cmap']
        for subtable in cmap_table.tables:
            try:
                if hasattr(subtable, 'cmap'):
                    for unicode_val, glyph_name in subtable.cmap.items():
                        unicode_map[glyph_name] = unicode_val
            except:
                continue
    except Exception as e:
        print(f"Warning: could not read cmap table: {e}", file=sys.stderr)
    return unicode_map


def extract_svg_path(font, glyph_name):
    """Extract SVG path data for a glyph."""
    glyph_set = font.getGlyphSet()
    try:
        glyph = glyph_set[glyph_name]

        svg_pen = SVGPathPen(glyph_set)
        bounds_pen = BoundsPen(glyph_set)

        glyph.draw(svg_pen)
        glyph.draw(bounds_pen)

        path = svg_pen.getCommands()
        bounds = bounds_pen.bounds

        return path, bounds
    except Exception as e:
        return "", None


def extract_glyph_map_cff(font_path, include_svg=True):
    """Extract glyph map from CFF font format."""
    with open(font_path, 'rb') as f:
        data = f.read()
    try:
        cff = CFFFontSet()
        cff.decompile(BytesIO(data), None)
    except Exception as e:
        print(f"Error: could not parse font as CFF format: {e}", file=sys.stderr)
        return None

    all_glyphs = []

    for font_name in cff.keys():
        font_dict = cff[font_name]
        charstrings = font_dict.CharStrings
        charset = font_dict.charset

        # print(f"Processing font: {font_name}")
        # print(f"Total glyphs: {len(charset)}")

        for i, glyph_name in enumerate(charset):
            unicode_val = STANDARD_ENCODING_UNICODE.get(glyph_name)
            unicode_hex = f"U+{unicode_val:04X}" if unicode_val else "N/A"

            char_repr = chr(unicode_val) if unicode_val and unicode_val >= 32 else ""

            charstring = charstrings[glyph_name]
            svg_path = ""
            bounds = None

            if include_svg:
                try:
                    svg_pen = SVGPathPen(None)
                    bounds_pen = BoundsPen(None)
                    charstring.draw(svg_pen)
                    charstring.draw(bounds_pen)
                    svg_path = svg_pen.getCommands()
                    bounds = bounds_pen.bounds
                except Exception as e:
                    print(f"Warning: Could not extract path for '{glyph_name}': {e}", file=sys.stderr)

            glyph_info = {
                'index': i,
                'glyph_name': glyph_name,
                'unicode_hex': unicode_hex,
                'unicode_dec': unicode_val if unicode_val else None,
                'character': char_repr,
                'left_side_bearing': "",
                'bounds': bounds,
                'is_composite': "",
            }

            if include_svg:
                glyph_info["svg_path"] = svg_path
                glyph_info["bounds"] = bounds

            all_glyphs.append(glyph_info)
    return all_glyphs


def extract_glyph_map(font_path, include_svg=True, max_glyphs=None):
    """Extract glyph map from TTF font format."""
    try:
        font = TTFont(font_path, recalcBBoxes=False, recalcTimestamp=False)
    except Exception as e:
        print(f"Error extraction: {e}")
        return None

    try:
        glyph_order = font.getGlyphOrder()
        print(f"✓ Got glyph order from font")
    except:
        try:
            glyf_table = font["glyf"]
            glyph_order = list(glyf_table.keys())
        except Exception as e:
            print(e)
            return None

    unicode_map = extract_unicode_mappings(font)

    try:
        glyf_table = font["glyf"]
        hmtx_table = font["hmtx"]
    except Exception as e:
        print(f"Error missing required tables: {e}", file=sys.stderr)
        return None

    font_name = "Unknown"
    try:
        name_table = font['name']
        for record in name_table.names:
            if record.nameID == 1:
                font_name = record.toUnicode()
                break
    except:
        pass
    """
    print(f"Processing font {font_name}")
    print(f"Total glyphs: {len(glyph_order)}")
    print(f"Unicode mappings: {len(unicode_map)}")
    """
    if max_glyphs:
        glyph_order = glyph_order[:max_glyphs]
        print(f"Limiting to first {max_glyphs} glyphs")

    all_glyphs = []

    for i, glyph_name in enumerate(glyph_order):
        unicode_val = unicode_map.get(glyph_name)
        if unicode_val is None:
            continue
        unicode_hex = f"U+{unicode_val:04X}" if unicode_val else "N/A"
        char_repr = chr(unicode_val) if unicode_val and 32 <= unicode_val < 0x10000 else ""

        try:
            width, lsb = hmtx_table[glyph_name]
        except:
            width, lsb = 0, 0

        bounds = None
        is_composite = False

        try:
            glyph = glyf_table[glyph_name]
            if hasattr(glyph, 'xMin') and glyph.xMin is not None:
                bounds = [glyph.xMin, glyph.yMin, glyph.xMax, glyph.yMax]
            if hasattr(glyph, 'isComposite'):
                is_composite = glyph.isComposite()
        except:
            pass

        svg_path = ""

        if include_svg and bounds:
            svg_path, _ = extract_svg_path(font, glyph_name)

        glyph_info = {
            'index': i,
            'glyph_name': glyph_name,
            'unicode_hex': unicode_hex,
            'unicode_dec': unicode_val,
            'character': char_repr,
            'width': width,
            'left_side_bearing': lsb,
            'bounds': bounds,
            'is_composite': is_composite,
        }

        if include_svg:
            glyph_info['svg_path'] = svg_path
        all_glyphs.append(glyph_info)

    return all_glyphs


def print_table(glyphs, max_rows=None):
    """Print glyph data in table format."""
    print("\n" + "=" * 110)
    print(f"{'Idx':<6} {'Glyph Name':<30} {'Unicode':<12} {'Dec':<8} {'Char':<6} {'Width':<8} {'Type':<10} {'Bounds'}")

    display_glyphs = glyphs[:max_rows] if max_rows else glyphs
    print(f"Displaying {len(display_glyphs)} glyphs")
    for glyph in display_glyphs:
        if glyph['unicode_dec'] is None:
            continue
        char_display = repr(glyph['character']) if glyph['character'] else "-"
        unicode_dec = str(glyph['unicode_dec']) if glyph['unicode_dec'] is not None else ""

        glyph_type = "composite" if glyph['is_composite'] else "simple" if glyph.get('bounds') else "empty"
        bounds_str = str(glyph.get('bounds'))[:30] if glyph.get('bounds') else 'None'

        print(f"{glyph['index']:<6} {glyph['glyph_name']:<30} {glyph['unicode_hex']:<12}"
              f"{unicode_dec:<8} {char_display:<6} {glyph.get('width', 0):<8} {glyph_type:<10} {bounds_str}")

    if max_rows and len(glyphs) > max_rows:
        print(f"\n... and {len(glyphs) - max_rows} more glyphs")

    print("=" * 100 + "\n")


def sort_map_by_unicode(glyph_map):
    """Sort glyph map by Unicode value."""
    glyph_map.sort(key=lambda x: x['unicode_dec'] if x['unicode_dec'] is not None else -1)
    return glyph_map


def sort_and_merge_glyphs(glyph_list):
    """Sort and merge duplicate glyphs."""
    glyph_list.sort(key=lambda x: (x.get('unicode_dec') or -1, x.get('index', 0)))

    merged_map = {}

    for glyph in glyph_list:
        bounds_sig = tuple(glyph['bounds']) if glyph['bounds'] is not None else None
        signature = (bounds_sig, glyph['svg_path'], glyph['unicode_dec'])

        if signature not in merged_map:
            if 'aliases' not in glyph:
                glyph['aliases'] = []
            merged_map[signature] = glyph

        else:
            # --- DUPLICATE FOUND (MERGE) ---
            primary = merged_map[signature]
            secondary_name = glyph['glyph_name']

            primary_is_generic = primary['glyph_name'].startswith('glyph')
            secondary_is_generic = secondary_name.startswith('glyph')

            if primary_is_generic and not secondary_is_generic:
                # Swap: Make Secondary the main name, put Primary name in aliases
                old_name = primary['glyph_name']
                primary['glyph_name'] = secondary_name
                if old_name not in primary['aliases']:
                    primary['aliases'].append(old_name)
            else:
                # Standard: Keep Primary name, put Secondary name in aliases
                if secondary_name != primary['glyph_name'] and secondary_name not in primary['aliases']:
                    primary['aliases'].append(secondary_name)

            # (Optional) Merge existing aliases from the secondary object if they exist
            if 'aliases' in glyph:
                for alias in glyph['aliases']:
                    if alias not in primary['aliases'] and alias != primary['glyph_name']:
                        primary['aliases'].append(alias)

    # Convert the map values back to a list and sort by index again for cleanliness
    result_list = list(merged_map.values())
    result_list.sort(key=lambda x: x.get('index', 0))

    return result_list

def merge_glyph_maps(existing_glyph_maps, new_glyph_maps):
    """Merge new glyph maps with existing ones."""
    existing_names = {item['glyph_name'] for item in existing_glyph_maps}
    #print(f"Existing glyph maps: {existing_names}")
    for item in new_glyph_maps:
        name = item.get('glyph_name')

        if name not in existing_names:
            existing_glyph_maps.append(item)
            existing_names.add(name)
            #print(f"{name} added to existing glyph map")

    sorted_glyph_maps = sort_and_merge_glyphs(existing_glyph_maps)
    return sorted_glyph_maps

def detect_font_type(font_list):
    for font_info in font_list:
        font_name = font_info[3]
        if 'Kepatihan' in font_name:
            return font_info[0], font_info[1], 'kepatihan'
        elif 'Balungan' in font_name:
            return font_info[0], font_info[1], 'balungan'
    return None,None,None

def parse_pdf_font(pdf_path, output_dir=None):
    if output_dir is None:
        output_dir = Path.cwd()
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF:{e}")
        return None

    # Get fonts from first page
    page_0 = doc[0]
    fonts = page_0.get_fonts()
    font_xref, font_format, font_type = detect_font_type(fonts)

    if not font_xref:
        print(f"No Balungan or Kepatihan font found in {pdf_path}")
        return None

    #print(f"Found {font_type} font in {pdf_path}, xref: {font_xref}, format: {font_format}")

    font_data = doc.extract_font(font_xref)

    if font_format == 'cff':
        temp_font_file = output_dir/f"temp_{font_type}.cff"
    else:
        temp_font_file = output_dir/f"temp_{font_type}.ttf"

    output_json = output_dir/f"map_{font_type}.json"

    # Write font file
    with open(temp_font_file, "wb") as f:
        f.write(font_data[3])
    #print(f"Font file {temp_font_file} written")

    # Load existing glyph map if it exists
    if output_json.is_file():
        with open(output_json, "r") as f:
            glyphs_map_existing = json.load(f)
    else:
        glyphs_map_existing = []

    # Extract glyphs from font
    if font_format == "cff":
        glyphs_map_extracted = extract_glyph_map_cff(str(temp_font_file), include_svg=True)
    else:
        glyphs_map_extracted = extract_glyph_map(str(temp_font_file), include_svg=True)

    if glyphs_map_extracted is None:
        print("Failed to extract glyph map")
        return None

    # Merge with existing data
    merged_glyph = merge_glyph_maps(glyphs_map_existing, glyphs_map_extracted)

    # Export to JSON
    export_to_json(merged_glyph, str(output_json))

    # Print summary if requested
    # print_table(merged_glyph)
    """
    print(f"\nSummary:")
    print(f" Total glyphs: {len(merged_glyph)}")
    print(f" With unicode: {sum(1 for g in merged_glyph if g['unicode_dec'] is not None)}")
    print(f" With paths: {sum(1 for g in merged_glyph if g.get('svg_path'))}")
    """
    return {
        'font_type': font_type,
        'glyphs': merged_glyph,
        'output_file': str(output_json),
        'temp_font_file': str(temp_font_file)
    }

