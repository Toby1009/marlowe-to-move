#!/usr/bin/env python3
"""
Deterministic Marlowe JSON AST -> BPMN 2.0 XML conversion.

This module targets the Marlowe subset used in this repository and emits
standards-shaped BPMN XML with BPMN DI coordinates for direct import into BPMN
tools.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional
import xml.etree.ElementTree as ET

from marlowe_types import (
    AccountPayee,
    AddValue,
    AndObs,
    Assert,
    AvailableMoney,
    Case,
    Choice,
    ChoiceValue,
    ChoseSomething,
    Close,
    Cond,
    Constant,
    Contract,
    Deposit,
    DivValue,
    FalseObs,
    If,
    Let,
    MulValue,
    NegValue,
    NotObs,
    Notify,
    Observation,
    OrObs,
    Party,
    PartyPayee,
    Pay,
    Payee,
    RoleParty,
    AddressParty,
    SubValue,
    TimeIntervalEnd,
    TimeIntervalStart,
    Token,
    TrueObs,
    UseValue,
    Value,
    ValueEQ,
    ValueGE,
    ValueGT,
    ValueLE,
    ValueLT,
    When,
)

BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI_NS = "http://www.omg.org/spec/BPMN/20100524/DI"
DC_NS = "http://www.omg.org/spec/DD/20100524/DC"
DI_NS = "http://www.omg.org/spec/DD/20100524/DI"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

ET.register_namespace("bpmn", BPMN_NS)
ET.register_namespace("bpmndi", BPMNDI_NS)
ET.register_namespace("dc", DC_NS)
ET.register_namespace("di", DI_NS)
ET.register_namespace("xsi", XSI_NS)

NODE_SIZES = {
    "startEvent": (36, 36),
    "endEvent": (36, 36),
    "intermediateCatchEvent": (36, 36),
    "serviceTask": (120, 80),
    "scriptTask": (120, 80),
    "receiveTask": (120, 80),
    "exclusiveGateway": (50, 50),
    "eventBasedGateway": (50, 50),
}


@dataclass
class BpmnNode:
    id: str
    tag: str
    name: str
    x: int
    y: int
    width: int
    height: int
    lane: str
    attrs: Dict[str, str] = field(default_factory=dict)
    documentation: Optional[str] = None
    timer_iso: Optional[str] = None
    condition_text: Optional[str] = None

    @property
    def center_y(self) -> int:
        return self.y + self.height // 2

    @property
    def right_x(self) -> int:
        return self.x + self.width

    @property
    def left_x(self) -> int:
        return self.x


@dataclass
class BpmnSequenceFlow:
    id: str
    source_ref: str
    target_ref: str
    name: Optional[str] = None
    condition_text: Optional[str] = None


@dataclass
class BpmnLane:
    id: str
    name: str
    y: int
    height: int
    node_ids: List[str]


class MarloweToBpmnConverter:
    H_STEP = 220
    V_STEP = 160
    LANE_HEADER_WIDTH = 160
    LANE_PADDING_Y = 40
    LANE_ROW_STEP = 110
    POOL_MARGIN = 40

    def __init__(self) -> None:
        self._node_counter = 0
        self._flow_counter = 0
        self.nodes: Dict[str, BpmnNode] = {}
        self.flows: List[BpmnSequenceFlow] = []
        self.lanes: List[BpmnLane] = []
        self.participant_bounds: Dict[str, int] = {"x": 0, "y": 0, "width": 0, "height": 0}

    def generate_xml(self, contract: Contract, process_name: str = "Marlowe Contract") -> str:
        self.nodes.clear()
        self.flows.clear()
        self._node_counter = 0
        self._flow_counter = 0

        start_id = self._add_node("startEvent", "Contract start", 80, 120, lane="Contract")
        self._emit_contract(contract, start_id, 220, 120)
        self._layout_lanes()

        definitions = ET.Element(
            self._qname(BPMN_NS, "definitions"),
            {
                "id": "Definitions_MarloweBPMN",
                "targetNamespace": "https://marlowe-to-move.local/bpmn",
            },
        )
        process = ET.SubElement(
            definitions,
            self._qname(BPMN_NS, "process"),
            {
                "id": "Process_MarloweContract",
                "name": process_name,
                "isExecutable": "false",
            },
        )
        doc = ET.SubElement(process, self._qname(BPMN_NS, "documentation"))
        doc.text = (
            "Deterministic BPMN projection of a Marlowe contract. "
            "Gateway labels and event names preserve the original Marlowe semantics."
        )

        lane_set = ET.SubElement(process, self._qname(BPMN_NS, "laneSet"), {"id": "LaneSet_1"})
        for lane in self.lanes:
            lane_el = ET.SubElement(
                lane_set,
                self._qname(BPMN_NS, "lane"),
                {"id": lane.id, "name": lane.name},
            )
            for node_id in lane.node_ids:
                ET.SubElement(lane_el, self._qname(BPMN_NS, "flowNodeRef")).text = node_id

        incoming_map, outgoing_map = self._build_io_maps()
        for node in self.nodes.values():
            node_el = ET.SubElement(
                process,
                self._qname(BPMN_NS, node.tag),
                {"id": node.id, "name": node.name, **node.attrs},
            )
            for flow_id in incoming_map.get(node.id, []):
                ET.SubElement(node_el, self._qname(BPMN_NS, "incoming")).text = flow_id
            for flow_id in outgoing_map.get(node.id, []):
                ET.SubElement(node_el, self._qname(BPMN_NS, "outgoing")).text = flow_id
            if node.documentation:
                ET.SubElement(node_el, self._qname(BPMN_NS, "documentation")).text = node.documentation
            if node.timer_iso is not None:
                timer_def = ET.SubElement(node_el, self._qname(BPMN_NS, "timerEventDefinition"))
                time_date = ET.SubElement(timer_def, self._qname(BPMN_NS, "timeDate"))
                time_date.text = node.timer_iso
            if node.condition_text is not None:
                cond_def = ET.SubElement(node_el, self._qname(BPMN_NS, "conditionalEventDefinition"))
                condition = ET.SubElement(
                    cond_def,
                    self._qname(BPMN_NS, "condition"),
                    {self._qname(XSI_NS, "type"): "bpmn:tFormalExpression"},
                )
                condition.text = node.condition_text

        for flow in self.flows:
            attrs = {
                "id": flow.id,
                "sourceRef": flow.source_ref,
                "targetRef": flow.target_ref,
            }
            if flow.name:
                attrs["name"] = flow.name
            flow_el = ET.SubElement(process, self._qname(BPMN_NS, "sequenceFlow"), attrs)
            if flow.condition_text:
                expr = ET.SubElement(
                    flow_el,
                    self._qname(BPMN_NS, "conditionExpression"),
                    {self._qname(XSI_NS, "type"): "bpmn:tFormalExpression"},
                )
                expr.text = flow.condition_text

        collaboration = ET.SubElement(
            definitions,
            self._qname(BPMN_NS, "collaboration"),
            {"id": "Collaboration_MarloweContract"},
        )
        ET.SubElement(
            collaboration,
            self._qname(BPMN_NS, "participant"),
            {
                "id": "Participant_MarloweContract",
                "name": process_name,
                "processRef": "Process_MarloweContract",
            },
        )

        diagram = ET.SubElement(
            definitions,
            self._qname(BPMNDI_NS, "BPMNDiagram"),
            {"id": "BPMNDiagram_MarloweContract"},
        )
        plane = ET.SubElement(
            diagram,
            self._qname(BPMNDI_NS, "BPMNPlane"),
            {"id": "BPMNPlane_MarloweContract", "bpmnElement": "Collaboration_MarloweContract"},
        )

        participant_shape = ET.SubElement(
            plane,
            self._qname(BPMNDI_NS, "BPMNShape"),
            {"id": "Participant_MarloweContract_di", "bpmnElement": "Participant_MarloweContract", "isHorizontal": "true"},
        )
        ET.SubElement(
            participant_shape,
            self._qname(DC_NS, "Bounds"),
            {
                "x": str(self.participant_bounds["x"]),
                "y": str(self.participant_bounds["y"]),
                "width": str(self.participant_bounds["width"]),
                "height": str(self.participant_bounds["height"]),
            },
        )

        lane_x = self.participant_bounds["x"]
        lane_width = self.participant_bounds["width"]
        for lane in self.lanes:
            lane_shape = ET.SubElement(
                plane,
                self._qname(BPMNDI_NS, "BPMNShape"),
                {"id": f"{lane.id}_di", "bpmnElement": lane.id, "isHorizontal": "true"},
            )
            ET.SubElement(
                lane_shape,
                self._qname(DC_NS, "Bounds"),
                {
                    "x": str(lane_x),
                    "y": str(lane.y),
                    "width": str(lane_width),
                    "height": str(lane.height),
                },
            )

        for node in self.nodes.values():
            shape = ET.SubElement(
                plane,
                self._qname(BPMNDI_NS, "BPMNShape"),
                {"id": f"{node.id}_di", "bpmnElement": node.id},
            )
            ET.SubElement(
                shape,
                self._qname(DC_NS, "Bounds"),
                {
                    "x": str(node.x),
                    "y": str(node.y),
                    "width": str(node.width),
                    "height": str(node.height),
                },
            )

        for flow in self.flows:
            edge = ET.SubElement(
                plane,
                self._qname(BPMNDI_NS, "BPMNEdge"),
                {"id": f"{flow.id}_di", "bpmnElement": flow.id},
            )
            for x, y in self._edge_waypoints(self.nodes[flow.source_ref], self.nodes[flow.target_ref]):
                ET.SubElement(edge, self._qname(DI_NS, "waypoint"), {"x": str(x), "y": str(y)})

        self._indent(definitions)
        return ET.tostring(definitions, encoding="unicode", xml_declaration=True)

    def generate_svg(self, contract: Contract, process_name: str = "Marlowe Contract") -> str:
        self.generate_xml(contract, process_name=process_name)
        width = self.participant_bounds["x"] + self.participant_bounds["width"] + self.POOL_MARGIN
        height = self.participant_bounds["y"] + self.participant_bounds["height"] + self.POOL_MARGIN
        svg = ET.Element(
            "svg",
            {
                "xmlns": "http://www.w3.org/2000/svg",
                "width": str(width),
                "height": str(height),
                "viewBox": f"0 0 {width} {height}",
            },
        )
        defs = ET.SubElement(svg, "defs")
        marker = ET.SubElement(
            defs,
            "marker",
            {
                "id": "arrowhead",
                "markerWidth": "10",
                "markerHeight": "7",
                "refX": "9",
                "refY": "3.5",
                "orient": "auto",
                "markerUnits": "strokeWidth",
            },
        )
        ET.SubElement(marker, "polygon", {"points": "0 0, 10 3.5, 0 7", "fill": "#334155"})

        ET.SubElement(svg, "rect", {"x": "0", "y": "0", "width": str(width), "height": str(height), "fill": "#ffffff"})
        ET.SubElement(
            svg,
            "rect",
            {
                "x": str(self.participant_bounds["x"]),
                "y": str(self.participant_bounds["y"]),
                "width": str(self.participant_bounds["width"]),
                "height": str(self.participant_bounds["height"]),
                "fill": "#f8fafc",
                "stroke": "#94a3b8",
                "stroke-width": "2",
            },
        )
        for lane in self.lanes:
            ET.SubElement(
                svg,
                "rect",
                {
                    "x": str(self.participant_bounds["x"]),
                    "y": str(lane.y),
                    "width": str(self.participant_bounds["width"]),
                    "height": str(lane.height),
                    "fill": "#ffffff",
                    "stroke": "#cbd5e1",
                    "stroke-width": "1",
                },
            )
            ET.SubElement(
                svg,
                "rect",
                {
                    "x": str(self.participant_bounds["x"]),
                    "y": str(lane.y),
                    "width": str(self.LANE_HEADER_WIDTH),
                    "height": str(lane.height),
                    "fill": "#e2e8f0",
                    "stroke": "#cbd5e1",
                    "stroke-width": "1",
                },
            )
            label = ET.SubElement(
                svg,
                "text",
                {
                    "x": str(self.participant_bounds["x"] + 18),
                    "y": str(lane.y + 28),
                    "font-family": "monospace",
                    "font-size": "16",
                    "font-weight": "700",
                    "fill": "#0f172a",
                },
            )
            label.text = lane.name

        for flow in self.flows:
            points = list(self._edge_waypoints(self.nodes[flow.source_ref], self.nodes[flow.target_ref]))
            ET.SubElement(
                svg,
                "polyline",
                {
                    "points": " ".join(f"{x},{y}" for x, y in points),
                    "fill": "none",
                    "stroke": "#334155",
                    "stroke-width": "2",
                    "marker-end": "url(#arrowhead)",
                },
            )

        for node in self.nodes.values():
            self._append_svg_node(svg, node)

        self._indent(svg)
        return ET.tostring(svg, encoding="unicode", xml_declaration=True)

    def _emit_contract(
        self,
        contract: Contract,
        incoming_id: str,
        x: int,
        y: int,
        flow_name: Optional[str] = None,
        flow_condition: Optional[str] = None,
    ) -> None:
        if isinstance(contract, Close):
            end_id = self._add_node("endEvent", "Close", x, y, lane="Contract")
            self._add_flow(incoming_id, end_id, name=flow_name, condition_text=flow_condition)
            return

        if isinstance(contract, Pay):
            name = (
                f"Pay {self._format_value(contract.value)} {self._format_token(contract.token)} "
                f"from {self._format_party(contract.from_account)} to {self._format_payee(contract.to)}"
            )
            node_id = self._add_node("serviceTask", name, x, y, lane="Contract")
            self._add_flow(incoming_id, node_id, name=flow_name, condition_text=flow_condition)
            self._emit_contract(contract.then, node_id, x + self.H_STEP, y)
            return

        if isinstance(contract, Let):
            node_id = self._add_node(
                "scriptTask",
                f"Let {contract.name} = {self._format_value(contract.value)}",
                x,
                y,
                lane="Contract",
            )
            self._add_flow(incoming_id, node_id, name=flow_name, condition_text=flow_condition)
            self._emit_contract(contract.then, node_id, x + self.H_STEP, y)
            return

        if isinstance(contract, Assert):
            node_id = self._add_node(
                "scriptTask",
                f"Assert {self._format_observation(contract.obs)}",
                x,
                y,
                lane="Contract",
            )
            self._add_flow(incoming_id, node_id, name=flow_name, condition_text=flow_condition)
            self._emit_contract(contract.then, node_id, x + self.H_STEP, y)
            return

        if isinstance(contract, If):
            gateway_id = self._add_node(
                "exclusiveGateway",
                self._truncate(f"If {self._format_observation(contract.cond)}"),
                x,
                y,
                lane="Contract",
                attrs={"gatewayDirection": "Diverging"},
                documentation=self._format_observation(contract.cond),
            )
            self._add_flow(incoming_id, gateway_id, name=flow_name, condition_text=flow_condition)

            then_y = y - self.V_STEP // 2
            else_y = y + self.V_STEP // 2
            cond_text = self._format_observation(contract.cond)
            then_flow_id = self._peek_next_flow_id()
            self._emit_contract(
                contract.then,
                gateway_id,
                x + self.H_STEP,
                then_y,
                flow_name="then",
                flow_condition=cond_text,
            )
            self.nodes[gateway_id].attrs["default"] = self._peek_next_flow_id()
            self._emit_contract(
                contract.else_,
                gateway_id,
                x + self.H_STEP,
                else_y,
                flow_name="else",
                flow_condition=f"not ({cond_text})",
            )
            if then_flow_id == self.nodes[gateway_id].attrs["default"]:
                self.nodes[gateway_id].attrs.pop("default", None)
            return

        if isinstance(contract, When):
            gateway_id = self._add_node(
                "eventBasedGateway",
                self._truncate(f"Await action before {self._format_timeout(contract.timeout)}"),
                x,
                y,
                lane="Contract",
                attrs={"gatewayDirection": "Diverging"},
                documentation=(
                    f"Marlowe When with {len(contract.cases)} case(s) and timeout "
                    f"{self._format_timeout(contract.timeout)}"
                ),
            )
            self._add_flow(incoming_id, gateway_id, name=flow_name, condition_text=flow_condition)
            branch_positions = self._distribute_rows(y, len(contract.cases) + 1)
            for index, case in enumerate(contract.cases):
                action_id = self._emit_action(case, x + self.H_STEP, branch_positions[index])
                self._add_flow(gateway_id, action_id, name=self._action_edge_name(case))
                self._emit_contract(case.then, action_id, x + (self.H_STEP * 2), branch_positions[index])

            timeout_y = branch_positions[-1]
            timer_id = self._add_node(
                "intermediateCatchEvent",
                f"Timeout at {self._format_timeout(contract.timeout)}",
                x + self.H_STEP,
                timeout_y,
                lane="Contract",
                timer_iso=self._format_time_iso(contract.timeout),
                documentation=f"Marlowe timeout branch for UNIX timestamp {contract.timeout}",
            )
            self._add_flow(gateway_id, timer_id, name="timeout")
            self._emit_contract(
                contract.timeout_continuation,
                timer_id,
                x + (self.H_STEP * 2),
                timeout_y,
            )
            return

        raise TypeError(f"Unsupported contract node for BPMN conversion: {type(contract).__name__}")

    def _emit_action(self, case: Case, x: int, y: int) -> str:
        action = case.action
        if isinstance(action, Deposit):
            name = (
                f"Receive deposit {self._format_value(action.amount)} {self._format_token(action.token)} "
                f"from {self._format_party(action.party)}"
            )
            return self._add_node(
                "receiveTask",
                name,
                x,
                y,
                lane=self._format_party(action.party),
                documentation=(
                    f"into_account={self._format_party(action.into_account)}, "
                    f"party={self._format_party(action.party)}"
                ),
            )

        if isinstance(action, Choice):
            bounds = ", ".join(f"[{bound.from_value}..{bound.to_value}]" for bound in action.bounds)
            return self._add_node(
                "receiveTask",
                f"Receive choice {action.choice_id.name} from {self._format_party(action.choice_id.by)} {bounds}",
                x,
                y,
                lane=self._format_party(action.choice_id.by),
                documentation=f"choice_owner={self._format_party(action.choice_id.by)}",
            )

        if isinstance(action, Notify):
            return self._add_node(
                "intermediateCatchEvent",
                self._truncate(f"Notify when {self._format_observation(action.observation)}"),
                x,
                y,
                lane="Contract",
                condition_text=self._format_observation(action.observation),
                documentation="Marlowe Notify waits until the observation becomes true.",
            )

        raise TypeError(f"Unsupported action node for BPMN conversion: {type(action).__name__}")

    def _action_edge_name(self, case: Case) -> str:
        action = case.action
        if isinstance(action, Deposit):
            return self._truncate(f"deposit by {self._format_party(action.party)}")
        if isinstance(action, Choice):
            return self._truncate(f"choice by {self._format_party(action.choice_id.by)}")
        if isinstance(action, Notify):
            return self._truncate("notify")
        return "case"

    def _add_node(
        self,
        tag: str,
        name: str,
        x: int,
        y: int,
        lane: str,
        attrs: Optional[Dict[str, str]] = None,
        documentation: Optional[str] = None,
        timer_iso: Optional[str] = None,
        condition_text: Optional[str] = None,
    ) -> str:
        self._node_counter += 1
        node_id = f"{tag}_{self._node_counter}"
        width, height = NODE_SIZES[tag]
        self.nodes[node_id] = BpmnNode(
            id=node_id,
            tag=tag,
            name=self._truncate(name),
            x=x,
            y=y,
            width=width,
            height=height,
            lane=lane,
            attrs=attrs or {},
            documentation=documentation,
            timer_iso=timer_iso,
            condition_text=condition_text,
        )
        return node_id

    def _add_flow(
        self,
        source_ref: str,
        target_ref: str,
        name: Optional[str] = None,
        condition_text: Optional[str] = None,
    ) -> str:
        self._flow_counter += 1
        flow_id = f"Flow_{self._flow_counter}"
        self.flows.append(
            BpmnSequenceFlow(
                id=flow_id,
                source_ref=source_ref,
                target_ref=target_ref,
                name=self._truncate(name) if name else None,
                condition_text=condition_text,
            )
        )
        return flow_id

    def _peek_next_flow_id(self) -> str:
        return f"Flow_{self._flow_counter + 1}"

    def _build_io_maps(self) -> tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        incoming: Dict[str, List[str]] = {}
        outgoing: Dict[str, List[str]] = {}
        for flow in self.flows:
            outgoing.setdefault(flow.source_ref, []).append(flow.id)
            incoming.setdefault(flow.target_ref, []).append(flow.id)
        return incoming, outgoing

    def _layout_lanes(self) -> None:
        if not self.nodes:
            return

        min_x = min(node.x for node in self.nodes.values())
        shift_x = max(0, self.POOL_MARGIN + self.LANE_HEADER_WIDTH - min_x)
        for node in self.nodes.values():
            node.x += shift_x

        lane_names = ["Contract"]
        for node in sorted(self.nodes.values(), key=lambda item: (item.y, item.x, item.id)):
            if node.lane not in lane_names:
                lane_names.append(node.lane)

        lanes: List[BpmnLane] = []
        current_y = self.POOL_MARGIN
        for index, lane_name in enumerate(lane_names):
            lane_nodes = [node for node in self.nodes.values() if node.lane == lane_name]
            lane_nodes.sort(key=lambda item: (item.y, item.x, item.id))
            row_positions = self._cluster_positions([node.y for node in lane_nodes])
            lane_height = max(
                180,
                (self.LANE_PADDING_Y * 2)
                + (max(0, len(row_positions) - 1) * self.LANE_ROW_STEP)
                + max((node.height for node in lane_nodes), default=80),
            )
            lane_top = current_y
            lanes.append(
                BpmnLane(
                    id=f"Lane_{index + 1}",
                    name=lane_name,
                    y=lane_top,
                    height=lane_height,
                    node_ids=[node.id for node in lane_nodes],
                )
            )
            for node in lane_nodes:
                row_index = self._closest_position_index(node.y, row_positions)
                node.y = lane_top + self.LANE_PADDING_Y + (row_index * self.LANE_ROW_STEP)
            current_y += lane_height

        max_right_x = max(node.right_x for node in self.nodes.values())
        self.lanes = lanes
        self.participant_bounds = {
            "x": self.POOL_MARGIN,
            "y": self.POOL_MARGIN,
            "width": max_right_x - self.POOL_MARGIN + self.POOL_MARGIN,
            "height": current_y - self.POOL_MARGIN,
        }

    def _cluster_positions(self, positions: List[int]) -> List[int]:
        clusters: List[int] = []
        for pos in positions:
            if not clusters or abs(pos - clusters[-1]) > (self.V_STEP // 2):
                clusters.append(pos)
        return clusters or [0]

    def _closest_position_index(self, value: int, positions: List[int]) -> int:
        best_index = 0
        best_distance = abs(value - positions[0])
        for index, pos in enumerate(positions[1:], start=1):
            distance = abs(value - pos)
            if distance < best_distance:
                best_index = index
                best_distance = distance
        return best_index

    def _edge_waypoints(self, source: BpmnNode, target: BpmnNode) -> Iterable[tuple[int, int]]:
        start = (source.right_x, source.center_y)
        end = (target.left_x, target.center_y)
        if source.center_y == target.center_y:
            return (start, end)

        mid_x = start[0] + max(40, (end[0] - start[0]) // 2)
        return (
            start,
            (mid_x, start[1]),
            (mid_x, end[1]),
            end,
        )

    def _append_svg_node(self, svg: ET.Element, node: BpmnNode) -> None:
        group = ET.SubElement(svg, "g", {"id": node.id})
        center_x = node.x + (node.width // 2)
        center_y = node.center_y
        if node.tag in {"startEvent", "endEvent", "intermediateCatchEvent"}:
            radius = min(node.width, node.height) // 2
            ET.SubElement(
                group,
                "circle",
                {
                    "cx": str(center_x),
                    "cy": str(center_y),
                    "r": str(radius),
                    "fill": "#ffffff",
                    "stroke": "#0f172a",
                    "stroke-width": "2",
                },
            )
            if node.tag == "intermediateCatchEvent":
                ET.SubElement(
                    group,
                    "circle",
                    {
                        "cx": str(center_x),
                        "cy": str(center_y),
                        "r": str(max(1, radius - 5)),
                        "fill": "none",
                        "stroke": "#0f172a",
                        "stroke-width": "1.5",
                    },
                )
        elif node.tag in {"exclusiveGateway", "eventBasedGateway"}:
            points = [
                (center_x, node.y),
                (node.right_x, center_y),
                (center_x, node.y + node.height),
                (node.x, center_y),
            ]
            ET.SubElement(
                group,
                "polygon",
                {
                    "points": " ".join(f"{x},{y}" for x, y in points),
                    "fill": "#f8fafc",
                    "stroke": "#0f172a",
                    "stroke-width": "2",
                },
            )
        else:
            ET.SubElement(
                group,
                "rect",
                {
                    "x": str(node.x),
                    "y": str(node.y),
                    "width": str(node.width),
                    "height": str(node.height),
                    "rx": "12",
                    "ry": "12",
                    "fill": "#ffffff",
                    "stroke": "#0f172a",
                    "stroke-width": "2",
                },
            )

        lines = self._wrap_text(node.name, 22)
        text_y = center_y - ((len(lines) - 1) * 9)
        for index, line in enumerate(lines[:4]):
            text = ET.SubElement(
                group,
                "text",
                {
                    "x": str(center_x),
                    "y": str(text_y + (index * 18)),
                    "text-anchor": "middle",
                    "font-family": "monospace",
                    "font-size": "12",
                    "fill": "#0f172a",
                },
            )
            text.text = line

    def _wrap_text(self, text: str, max_len: int) -> List[str]:
        words = text.split()
        if not words:
            return [text]
        lines: List[str] = []
        current = words[0]
        for word in words[1:]:
            if len(current) + 1 + len(word) <= max_len:
                current = f"{current} {word}"
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def _distribute_rows(self, center_y: int, count: int) -> List[int]:
        if count <= 1:
            return [center_y]
        offset = ((count - 1) * self.V_STEP) // 2
        return [center_y - offset + (index * self.V_STEP) for index in range(count)]

    def _format_party(self, party: Party) -> str:
        if isinstance(party, RoleParty):
            return party.role_token
        if isinstance(party, AddressParty):
            return party.address
        raise TypeError(f"Unsupported party type: {type(party).__name__}")

    def _format_payee(self, payee: Payee) -> str:
        if isinstance(payee, PartyPayee):
            return self._format_party(payee.party)
        if isinstance(payee, AccountPayee):
            return f"account:{self._format_party(payee.account)}"
        raise TypeError(f"Unsupported payee type: {type(payee).__name__}")

    def _format_token(self, token: Token) -> str:
        if token.currency_symbol:
            return f"{token.currency_symbol}.{token.token_name}"
        return token.token_name or "token"

    def _format_value(self, value: Value) -> str:
        if isinstance(value, Constant):
            return str(value.value)
        if isinstance(value, AvailableMoney):
            return f"available({self._format_token(value.token)} in {self._format_party(value.party)})"
        if isinstance(value, NegValue):
            return f"-({self._format_value(value.value)})"
        if isinstance(value, AddValue):
            return f"({self._format_value(value.lhs)} + {self._format_value(value.rhs)})"
        if isinstance(value, SubValue):
            return f"({self._format_value(value.lhs)} - {self._format_value(value.rhs)})"
        if isinstance(value, MulValue):
            return f"({self._format_value(value.lhs)} * {self._format_value(value.rhs)})"
        if isinstance(value, DivValue):
            return f"({self._format_value(value.lhs)} / {self._format_value(value.rhs)})"
        if isinstance(value, ChoiceValue):
            return f"choice({value.choice_id.name})"
        if isinstance(value, TimeIntervalStart):
            return "time_interval_start"
        if isinstance(value, TimeIntervalEnd):
            return "time_interval_end"
        if isinstance(value, UseValue):
            return f"use_value({value.value_id})"
        if isinstance(value, Cond):
            return (
                f"if {self._format_observation(value.condition)} then "
                f"{self._format_value(value.true_value)} else {self._format_value(value.false_value)}"
            )
        raise TypeError(f"Unsupported value type: {type(value).__name__}")

    def _format_observation(self, observation: Observation) -> str:
        if isinstance(observation, TrueObs):
            return "true"
        if isinstance(observation, FalseObs):
            return "false"
        if isinstance(observation, AndObs):
            return f"({self._format_observation(observation.left)} and {self._format_observation(observation.right)})"
        if isinstance(observation, OrObs):
            return f"({self._format_observation(observation.left)} or {self._format_observation(observation.right)})"
        if isinstance(observation, NotObs):
            return f"not ({self._format_observation(observation.obs)})"
        if isinstance(observation, ChoseSomething):
            return f"chose_something({observation.choice_id.name})"
        if isinstance(observation, ValueGE):
            return f"{self._format_value(observation.lhs)} >= {self._format_value(observation.rhs)}"
        if isinstance(observation, ValueGT):
            return f"{self._format_value(observation.lhs)} > {self._format_value(observation.rhs)}"
        if isinstance(observation, ValueLT):
            return f"{self._format_value(observation.lhs)} < {self._format_value(observation.rhs)}"
        if isinstance(observation, ValueLE):
            return f"{self._format_value(observation.lhs)} <= {self._format_value(observation.rhs)}"
        if isinstance(observation, ValueEQ):
            return f"{self._format_value(observation.lhs)} = {self._format_value(observation.rhs)}"
        raise TypeError(f"Unsupported observation type: {type(observation).__name__}")

    def _format_timeout(self, unix_ts: int) -> str:
        return self._format_time_iso(unix_ts)

    def _format_time_iso(self, unix_ts: int) -> str:
        return datetime.fromtimestamp(self._normalize_unix_ts(unix_ts), timezone.utc).isoformat().replace("+00:00", "Z")

    def _normalize_unix_ts(self, unix_ts: int) -> float:
        # Blockly and the repo presets use Unix milliseconds. Accept plain seconds too.
        return unix_ts / 1000 if unix_ts >= 100_000_000_000 else unix_ts

    def _truncate(self, text: str, limit: int = 120) -> str:
        if len(text) <= limit:
            return text
        return text[: limit - 3] + "..."

    def _qname(self, namespace: str, tag: str) -> str:
        return f"{{{namespace}}}{tag}"

    def _indent(self, elem: ET.Element, level: int = 0) -> None:
        indent = "\n" + ("  " * level)
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = indent + "  "
            for child in elem:
                self._indent(child, level + 1)
                if not child.tail or not child.tail.strip():
                    child.tail = indent + "  "
            if not elem[-1].tail or not elem[-1].tail.strip():
                elem[-1].tail = indent
        elif level and (not elem.tail or not elem.tail.strip()):
            elem.tail = indent


def generate_bpmn_xml(contract: Contract, process_name: str = "Marlowe Contract") -> str:
    """Convert a parsed Marlowe contract AST into BPMN 2.0 XML."""
    return MarloweToBpmnConverter().generate_xml(contract, process_name=process_name)


def generate_bpmn_svg(contract: Contract, process_name: str = "Marlowe Contract") -> str:
    """Render a parsed Marlowe contract AST into a standalone SVG diagram."""
    return MarloweToBpmnConverter().generate_svg(contract, process_name=process_name)
