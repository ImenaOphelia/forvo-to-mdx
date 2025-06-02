import os
import json
import re
from xml.etree import ElementTree as ET
import argparse
import copy

def load_country_mappings(mapping_file):
    with open(mapping_file, 'r') as f:
        mappings = json.load(f)
    
    return {m['original_name'].lower(): m for m in mappings}

def create_composite_icon(flag_path, gender_icon, output_path, position_offset=5):
    try:
        flag_tree = ET.parse(flag_path)
        flag_root = flag_tree.getroot()
        
        flag_width = float(flag_root.get('width', 24))
        flag_height = float(flag_root.get('height', 24))
        flag_viewbox = flag_root.get('viewBox', f'0 0 {flag_width} {flag_height}').split()
        
        vb_x, vb_y, vb_width, vb_height = map(float, flag_viewbox)
        
        icon_size = min(vb_width, vb_height) / 4
        
        composite = ET.Element('svg', {
            'xmlns': 'http://www.w3.org/2000/svg',
            'width': str(flag_width),
            'height': str(flag_height),
            'viewBox': ' '.join(flag_viewbox)
        })
        
        for child in flag_root:
            composite.append(copy.deepcopy(child))
        
        if gender_icon:
            x_pos = vb_x + vb_width - icon_size - position_offset
            y_pos = vb_y + vb_height - icon_size - position_offset
            
            gender_container = ET.SubElement(composite, 'g', {
                'transform': f'translate({x_pos}, {y_pos}) scale({icon_size/512})'
            })
            
            for elem in gender_icon:
                new_elem = copy.deepcopy(elem)
                gender_container.append(new_elem)
        
        tree = ET.ElementTree(composite)
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
        return True
    except Exception as e:
        print(f"Error creating {output_path}: {str(e)}")
        return False

def apply_colors_to_svg(svg_root, color):
    """Apply color to all fillable elements in an SVG"""
    if 'fill' not in svg_root.attrib:
        svg_root.set('fill', color)
    
    for elem in svg_root.iter():
        tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        
        if tag_name in ['defs', 'mask', 'clipPath', 'pattern', 'linearGradient', 'radialGradient']:
            continue
            
        if 'fill' in elem.attrib:
            if elem.attrib['fill'] not in ['none', 'transparent']:
                elem.attrib['fill'] = color
        else:
            if tag_name in ['path', 'circle', 'rect', 'ellipse', 'polygon', 'polyline', 'line']:
                elem.set('fill', color)

def main():
    parser = argparse.ArgumentParser(description='Create gender-country composite icons')
    parser.add_argument('input_file', help='Origins stats file')
    parser.add_argument('mapping_file', help='Country mappings')
    parser.add_argument('flags_dir', help='Directory containing flags')
    parser.add_argument('--venus', default='venus.svg', help='Path to Venus icon')
    parser.add_argument('--mars', default='mars.svg', help='Path to Mars icon')
    parser.add_argument('--output', default='icons', help='Output directory')
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    
    venus_tree = ET.parse(args.venus)
    venus_root = venus_tree.getroot()
    mars_tree = ET.parse(args.mars)
    mars_root = mars_tree.getroot()
    
    apply_colors_to_svg(venus_root, '#FF69B4')
    apply_colors_to_svg(mars_root, '#1E90FF')
    
    venus_children = list(venus_root)
    mars_children = list(mars_root)
    
    country_mappings = load_country_mappings(args.mapping_file)
    
    with open(args.input_file, 'r') as f:
        data = json.load(f)
        combinations = data['unique_combinations']
    
    success_count = 0
    for gender, country in combinations:
        country_lower = country.lower()
        
        if country_lower not in country_mappings:
            print(f"Country not mapped: {country} - Skipping")
            continue
            
        mapping = country_mappings[country_lower]
        
        if not mapping.get('flag_file'):
            print(f"No flag file for: {country} - Skipping")
            continue
            
        gender_safe = gender.lower().replace(' ', '_') if gender else ''
        country_safe = mapping['iso_code']
        if gender_safe:
            filename = f"{gender_safe}_{country_safe}.svg"
        else:
            filename = f"_{country_safe}.svg"
        
        output_path = os.path.join(args.output, filename)
        flag_path = os.path.join(args.flags_dir, mapping['flag_file'])
        
        if not os.path.exists(flag_path):
            print(f"Flag file missing: {flag_path} - Skipping")
            continue
        
        gender_svg = None
        if gender and 'female' in gender.lower():
            gender_svg = venus_children
        elif gender and 'male' in gender.lower():
            gender_svg = mars_children
        
        if create_composite_icon(flag_path, gender_svg, output_path):
            success_count += 1
            print(f"Created: {filename}")

    print(f"\nSuccessfully created {success_count} out of {len(combinations)} icons")

if __name__ == "__main__":
    main()