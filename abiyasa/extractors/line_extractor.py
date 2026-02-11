import re

import pdfplumber


class LineFilter:
    @staticmethod
    def parse_line_spec(line_spec):
        """
        Parse line specification with loop support
        Format: "1-5*2" (lines 1-5, repeat 2 times)
                "1,3,5*3" (lines 1,3,5 repeated 3 times)
        Returns: list to preserve order and repetition
        """
        if not line_spec or line_spec.strip() == '':
            return None

        line_numbers = []
        parts = [part.strip() for part in line_spec.split(',')]

        for part in parts:
            # Check for loop syntax: "1-5*2" or "3*4"
            loop_match = re.match(r'^(.+?)\*(\d+)$', part)

            if loop_match:
                range_part = loop_match.group(1).strip()
                repeat_count = int(loop_match.group(2))

                # Parse the range/number part
                temp_numbers = []
                if '-' in range_part:
                    try:
                        start, end = range_part.split('-')
                        start = int(start.strip())
                        end = int(end.strip())
                        temp_numbers = list(range(start, end + 1))
                    except ValueError:
                        print(f"  ⚠️  Warning: Invalid range specification '{range_part}', skipping")
                else:
                    try:
                        temp_numbers = [int(range_part)]
                    except ValueError:
                        print(f"  ⚠️  Warning: Invalid line number '{range_part}', skipping")

                # Add repeated sequence
                for _ in range(repeat_count):
                    line_numbers.extend(temp_numbers)

            elif '-' in part:
                # Regular range without loop
                try:
                    start, end = part.split('-')
                    start = int(start.strip())
                    end = int(end.strip())
                    line_numbers.extend(range(start, end + 1))
                except ValueError:
                    print(f"  ⚠️  Warning: Invalid range specification '{part}', skipping")
            else:
                # Single number without loop
                try:
                    line_numbers.append(int(part))
                except ValueError:
                    print(f"  ⚠️  Warning: Invalid line number '{part}', skipping")

        return line_numbers if line_numbers else None

    @staticmethod
    def parse_bracket_loop(line_spec):
        """
        Parse bracket loop syntax: "[1-4,8-10]*2"
        Returns: list of line numbers in order with repetition
        """
        bracket_match = re.match(r'^\[(.+?)\]\*(\d+)$', line_spec.strip())

        if bracket_match:
            inner_spec = bracket_match.group(1)
            repeat_count = int(bracket_match.group(2))

            # Parse the inner specification
            inner_lines = LineFilter.parse_line_spec(inner_spec)

            if inner_lines:
                result = []
                for _ in range(repeat_count):
                    result.extend(inner_lines)
                return result

        return None

    @staticmethod
    def filter_lines(lines, line_spec):
        """
        Filter lines based on specification (now returns list to preserve order)
        """
        if isinstance(line_spec, str):
            line_numbers = LineFilter.parse_line_spec(line_spec)
        else:
            line_numbers = line_spec

        if line_numbers is None:
            return [(i + 1, line) for i, line in enumerate(lines)]

        filtered = []
        for target_line_num in line_numbers:
            if 1 <= target_line_num <= len(lines):
                filtered.append((target_line_num, lines[target_line_num - 1]))
            else:
                print(f"  ⚠️  Warning: Line {target_line_num} out of range (page has {len(lines)} lines)")

        return filtered

    @staticmethod
    def parse_page_line_spec(line_spec):
        """
        Parse page-aware line specification with loop support
        Format: "p1:1-5*2,p2:3-7" or "p1:[1-4,8-10]*2" or "p1:all"
        Returns: dict {page_num: list of line numbers or 'all'}
        """
        if not line_spec or line_spec.strip() == '':
            return {1: 'all'}

        page_lines = {}

        # Split by page specifications (p1:..., p2:...)
        # Use regex to handle brackets properly
        page_parts = re.split(r',(?=p\d+:)', line_spec)

        for part in page_parts:
            part = part.strip()

            if ':' in part:
                # Page-specific format: "p2:1-5*2" or "p1:[1-4,8]*2"
                page_part, line_part = part.split(':', 1)
                page_num = int(page_part.strip().lstrip('p'))

                if line_part.strip().lower() == 'all':
                    page_lines[page_num] = 'all'
                else:
                    # Check for bracket loop first
                    bracket_lines = LineFilter.parse_bracket_loop(line_part)
                    if bracket_lines:
                        line_numbers = bracket_lines
                    else:
                        line_numbers = LineFilter.parse_line_spec(line_part)

                    if page_num in page_lines and page_lines[page_num] != 'all':
                        page_lines[page_num].extend(line_numbers)
                    else:
                        page_lines[page_num] = line_numbers
            else:
                # No page specified, default to page 1
                if 1 not in page_lines:
                    page_lines[1] = []

                bracket_lines = LineFilter.parse_bracket_loop(part)
                if bracket_lines:
                    line_numbers = bracket_lines
                else:
                    line_numbers = LineFilter.parse_line_spec(part)

                if line_numbers:
                    if page_lines[1] == 'all':
                        page_lines[1] = line_numbers
                    else:
                        page_lines[1].extend(line_numbers)

        return page_lines if page_lines else {1: 'all'}


def extract_kepatihan_from_pdf(pdf_path, line_spec):
    try:
        print(f"  📄 Reading PDF... ")
        page_line_spec = LineFilter.parse_page_line_spec(line_spec)

        print(f"  🔍 Filtering by page specification: {page_line_spec}")

        with pdfplumber.open(pdf_path) as pdf:
            extracted_data = {
                'num_pages': len(pdf.pages),
                'line_spec': line_spec,
                'page_line_spec': page_line_spec,
                'pages': []
            }

            for i, page in enumerate(pdf.pages):
                page_num = i + 1
                text = page.extract_text()

                if text:
                    lines = text.split('\n')

                    # Check if this page should be processed
                    if page_num in page_line_spec:
                        line_filter = page_line_spec[page_num]

                        if line_filter == 'all':
                            filtered_lines = [(j + 1, line) for j, line in enumerate(lines)]
                        else:
                            filtered_lines = LineFilter.filter_lines(lines, line_filter)

                        page_data = {
                            'page_number': page_num,
                            'total_lines': len(lines),
                            'extracted_lines': len(filtered_lines),
                            'lines': [(line_num, line.strip())
                                      for line_num, line in filtered_lines if line.strip()],
                            'full_text': text
                        }
                        extracted_data['pages'].append(page_data)
                    else:
                        # Page not in spec, skip it
                        print(f"  ⏭️  Skipping page {page_num} (not in specification)")
                else:
                    print(f"  ⚠️  No text inside page {page_num}")

            print(f"  ✓  Extracted text from {len(extracted_data['pages'])} pages")
            return extracted_data

    except FileNotFoundError:
        print("File not found")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None