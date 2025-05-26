"""
Compares VTODOs and VEVENTs in two iCalendar sources.
"""

from argparse import ArgumentParser
from dataclasses import dataclass

import vobject as vo
from vobject.base import Component, ContentLine


def get_sort_key(component):
    def get_uid():
        return component.get_child_value("uid", "")

    # it's not quite as simple as getUID, need to account for recurrenceID and sequence
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
    """Recursively walk the component's children, deleting extraneous details like X-VOBJ-ORIGINAL-TZID."""
    for comp in component.components():
        delete_extraneous(comp, ignore_dtstamp)
    for line in component.lines():
        if "X-VOBJ-ORIGINAL-TZID" in line.params:
            del line.params["X-VOBJ-ORIGINAL-TZID"]
    if ignore_dtstamp and hasattr(component, "dtstamp_list"):
        del component.dtstamp_list


@dataclass
class ObjectWithSides:
    left: Component | ContentLine
    right: Component | ContentLine


def _process_component_lists(left_list, right_list):
    output = []
    right_index, right_list_size = 0, len(right_list)

    for comp in left_list:
        if right_index >= right_list_size:
            output.append((comp, None))
            continue

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
            match_result = _process_component_pair(comp, right_comp)
            if match_result is not None:
                output.append(match_result)

    return output


def _process_component_pair(left_comp, right_comp):
    """Return None if a match, or a pair of components including UIDs and any differing children."""
    child_keys = ObjectWithSides(left=left_comp.contents, right=right_comp.contents)

    different_content_lines, different_components = [], {}

    for key, left_list in child_keys.left.items():
        right_list = right_comp.contents.get(key, [])
        if isinstance(left_list[0], vo.base.Component):
            comp_difference = _process_component_lists(left_list, right_list)
            if len(comp_difference) > 0:
                different_components[key] = comp_difference

        elif left_list != right_list:
            different_content_lines.append((left_list, right_list))

    for key, right_list in child_keys.right.items():
        if key not in child_keys.left:
            if isinstance(right_list[0], vo.base.Component):
                different_components[key] = ([], right_list)
            else:
                different_content_lines.append(([], right_list))

    if not different_content_lines and not different_components:
        return None

    _component = ObjectWithSides(left=vo.new_from_behavior(left_comp.name), right=vo.new_from_behavior(left_comp.name))
    # add a UID, if one existed, despite the fact that they'll always be the same
    uid = left_comp.get_child_value("uid")
    if uid is not None:
        _component.left.add("uid").value = uid
        _component.right.add("uid").value = uid

    for name, child_pair_list in different_components.items():
        left_components, right_components = zip(*child_pair_list)
        if len(left_components) > 0:
            _component.left.contents[name] = filter(None, left_components)
        if len(right_components) > 0:
            _component.right.contents[name] = filter(None, right_components)

    for left_child_line, right_child_line in different_content_lines:
        name = (left_child_line or right_child_line)[0].name
        if left_child_line is not None:
            _component.left.contents[name] = left_child_line
        if right_child_line is not None:
            _component.right.contents[name] = right_child_line

    return _component.left, _component.right


def diff(left, right):
    """
    Take two VCALENDAR components, compare VEVENTs and VTODOs in them, return a list of object pairs containing just
    UID and the bits that didn't match, using None for objects that weren't present in one version or the other.

    When there are multiple ContentLines in one VEVENT, for instance many DESCRIPTION lines, such lines original
    order is assumed to be meaningful.  Order is also preserved when comparing (the unlikely case of) multiple
    parameters of the same type in a ContentLine
    """

    vevents = _process_component_lists(
        sort_by_uid(getattr(left, "vevent_list", [])), sort_by_uid(getattr(right, "vevent_list", []))
    )

    vtodos = _process_component_lists(
        sort_by_uid(getattr(left, "vtodo_list", [])), sort_by_uid(getattr(right, "vtodo_list", []))
    )

    return vevents + vtodos


def pretty_diff(left_obj, right_obj):
    seperator_size = 15
    for left, right in diff(left_obj, right_obj):
        print("<" * seperator_size)
        if left is not None:
            left.pretty_print()
        print("=" * seperator_size)
        if right is not None:
            right.pretty_print()
        print(">" * seperator_size)


def get_arguments():
    parser = ArgumentParser(description="ics_diff will print a comparison of two iCalendar files ")
    parser.add_argument("-V", "--version", action="version", version=vo.VERSION)
    parser.add_argument(
        "-i",
        "--ignore-dtstamp",
        dest="ignore",
        action="store_true",
        default=False,
        help="ignore DTSTAMP lines [default: False]",
    )
    parser.add_argument("ics_file1", help="The first ics file to compare")
    parser.add_argument("ics_file2", help="The second ics file to compare")

    return parser.parse_args()


def main():
    args = get_arguments()
    with open(args.ics_file1) as f, open(args.ics_file2) as g:  # pylint:disable=w1514
        cal1 = vo.read_one(f)
        cal2 = vo.read_one(g)
    delete_extraneous(cal1, ignore_dtstamp=args.ignore)
    delete_extraneous(cal2, ignore_dtstamp=args.ignore)
    pretty_diff(cal1, cal2)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Aborted")
