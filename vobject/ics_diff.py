"""
Compares VTODOs and VEVENTs in two iCalendar sources.
"""

from argparse import ArgumentParser

import vobject as vo


def get_sort_key(component):
    def get_uid():
        return component.get_child_value("uid", "")

    # it's not quite as simple as getUID, need to account for recurrenceID and
    # sequence

    def get_sequence():
        sequence = component.get_child_value("sequence", 0)
        return f"{int(sequence):05d}"

    def get_recurrence_id():
        recurrence_id = component.get_child_value("recurrence_id", None)
        return "0000-00-00" if recurrence_id is None else recurrence_id.isoformat()

    return get_uid() + get_sequence() + get_recurrence_id()


def sort_by_uid(components):
    return sorted(components, key=get_sort_key)


def delete_extraneous(component, ignore_dtstamp=False):
    """
    Recursively walk the component's children, deleting extraneous details like
    X-VOBJ-ORIGINAL-TZID.
    """
    for comp in component.components():
        delete_extraneous(comp, ignore_dtstamp)
    for line in component.lines():
        if "X-VOBJ-ORIGINAL-TZID" in line.params:
            del line.params["X-VOBJ-ORIGINAL-TZID"]
    if ignore_dtstamp and hasattr(component, "dtstamp_list"):
        del component.dtstamp_list


def diff(left, right):
    """
    Take two VCALENDAR components, compare VEVENTs and VTODOs in them,
    return a list of object pairs containing just UID and the bits
    that didn't match, using None for objects that weren't present in one
    version or the other.

    When there are multiple ContentLines in one VEVENT, for instance many
    DESCRIPTION lines, such lines original order is assumed to be
    meaningful.  Order is also preserved when comparing (the unlikely case
    of) multiple parameters of the same type in a ContentLine

    """

    def process_component_lists(left_list, right_list):
        output = []
        right_index = 0
        right_list_size = len(right_list)

        for comp in left_list:
            if right_index >= right_list_size:
                output.append((comp, None))
            else:
                left_key = get_sort_key(comp)
                right_comp = right_list[right_index]
                right_key = get_sort_key(right_comp)
                while left_key > right_key:
                    output.append((None, right_comp))
                    right_index += 1
                    if right_index >= right_list_size:
                        output.append((comp, None))
                        break

                    right_comp = right_list[right_index]
                    right_key = get_sort_key(right_comp)

                if left_key < right_key:
                    output.append((comp, None))
                elif left_key == right_key:
                    right_index += 1
                    match_result = process_component_pair(comp, right_comp)
                    if match_result is not None:
                        output.append(match_result)

        return output

    def process_component_pair(left_comp, right_comp):
        """
        Return None if a match, or a pair of components including UIDs and
        any differing children.

        """
        left_child_keys = left_comp.contents.keys()
        right_child_keys = right_comp.contents.keys()

        different_content_lines = []
        different_components = {}

        for key in left_child_keys:
            right_list = right_comp.contents.get(key, [])
            if isinstance(left_comp.contents[key][0], vo.base.Component):
                comp_difference = process_component_lists(left_comp.contents[key], right_list)
                if len(comp_difference) > 0:
                    different_components[key] = comp_difference

            elif left_comp.contents[key] != right_list:
                different_content_lines.append((left_comp.contents[key], right_list))

        for key in right_child_keys:
            if key not in left_child_keys:
                if isinstance(right_comp.contents[key][0], vo.base.Component):
                    different_components[key] = ([], right_comp.contents[key])
                else:
                    different_content_lines.append(([], right_comp.contents[key]))

        if not different_content_lines and not different_components:
            return None

        _left = vo.new_from_behavior(left_comp.name)
        _right = vo.new_from_behavior(left_comp.name)
        # add a UID, if one existed, despite the fact that they'll always be the same
        uid = left_comp.get_child_value("uid")
        if uid is not None:
            _left.add("uid").value = uid
            _right.add("uid").value = uid

        for name, child_pair_list in different_components.items():
            left_components, right_components = zip(*child_pair_list)
            if len(left_components) > 0:
                # filter out None
                _left.contents[name] = filter(None, left_components)
            if len(right_components) > 0:
                # filter out None
                _right.contents[name] = filter(None, right_components)

        for left_child_line, right_child_line in different_content_lines:
            non_empty = left_child_line or right_child_line
            name = non_empty[0].name
            if left_child_line is not None:
                _left.contents[name] = left_child_line
            if right_child_line is not None:
                _right.contents[name] = right_child_line

        return _left, _right

    vevents = process_component_lists(
        sort_by_uid(getattr(left, "vevent_list", [])), sort_by_uid(getattr(right, "vevent_list", []))
    )

    vtodos = process_component_lists(
        sort_by_uid(getattr(left, "vtodo_list", [])), sort_by_uid(getattr(right, "vtodo_list", []))
    )

    return vevents + vtodos


def pretty_diff(left_obj, right_obj):
    for left, right in diff(left_obj, right_obj):
        print("<<<<<<<<<<<<<<<")
        if left is not None:
            left.pretty_print()
        print("===============")
        if right is not None:
            right.pretty_print()
        print(">>>>>>>>>>>>>>>\n")


def get_options():
    # Configuration options #
    usage = "usage: %prog [options] ics_file1 ics_file2"
    parser = ArgumentParser(usage=usage, description="ics_diff will print a comparison of two iCalendar files ")
    parser.add_argument("--version", action="version", version=vo.VERSION)
    parser.add_argument(
        "-i",
        "--ignore-dtstamp",
        dest="ignore",
        action="store_true",
        default=False,
        help="ignore DTSTAMP lines [default: False]",
    )

    (cmdline_options, args) = parser.parse_args()
    if len(args) < 2:
        print("error: too few arguments given\n")
        print(parser.format_help())
        return False, False

    return cmdline_options, args


def main():
    options, args = get_options()
    if args:
        ignore_dtstamp = options.ignore
        ics_file1, ics_file2 = args
        with open(ics_file1) as f, open(ics_file2) as g:
            cal1 = vo.read_one(f)
            cal2 = vo.read_one(g)
        delete_extraneous(cal1, ignore_dtstamp=ignore_dtstamp)
        delete_extraneous(cal2, ignore_dtstamp=ignore_dtstamp)
        pretty_diff(cal1, cal2)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Aborted")
