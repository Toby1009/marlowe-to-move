#!/usr/bin/env python3
"""Structural validator for generated BPMN XML."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple
import xml.etree.ElementTree as ET

BPMN_NS = {"bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL", "bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI"}

FLOW_NODE_TAGS = {
    "startEvent",
    "endEvent",
    "intermediateCatchEvent",
    "serviceTask",
    "scriptTask",
    "receiveTask",
    "exclusiveGateway",
    "eventBasedGateway",
}


def validate_bpmn_xml(xml_text: str) -> Tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        return [f"XML parse error: {exc}"], warnings

    process = root.find("bpmn:process", BPMN_NS)
    if process is None:
        errors.append("Missing bpmn:process")
        return errors, warnings

    collaboration = root.find("bpmn:collaboration", BPMN_NS)
    if collaboration is None:
        errors.append("Missing bpmn:collaboration")
    else:
        participant = collaboration.find("bpmn:participant", BPMN_NS)
        if participant is None:
            errors.append("Missing bpmn:participant")
        elif participant.get("processRef") != process.get("id"):
            errors.append("participant.processRef does not match process id")

    lane_set = process.find("bpmn:laneSet", BPMN_NS)
    if lane_set is None:
        errors.append("Missing bpmn:laneSet")

    nodes = {}
    for tag in FLOW_NODE_TAGS:
        for elem in process.findall(f"bpmn:{tag}", BPMN_NS):
            node_id = elem.get("id")
            if node_id:
                nodes[node_id] = elem

    if not nodes:
        errors.append("No supported BPMN flow nodes found")

    lane_refs = set()
    if lane_set is not None:
        lanes = lane_set.findall("bpmn:lane", BPMN_NS)
        if not lanes:
            errors.append("laneSet has no lanes")
        for lane in lanes:
            refs = [ref.text for ref in lane.findall("bpmn:flowNodeRef", BPMN_NS) if ref.text]
            if not refs:
                warnings.append(f"Lane {lane.get('id')} has no flowNodeRef")
            for ref in refs:
                lane_refs.add(ref)
                if ref not in nodes:
                    errors.append(f"Lane references unknown flow node: {ref}")

    for node_id in nodes:
        if lane_set is not None and node_id not in lane_refs:
            warnings.append(f"Flow node not assigned to any lane: {node_id}")

    flow_ids = set()
    for flow in process.findall("bpmn:sequenceFlow", BPMN_NS):
        flow_id = flow.get("id")
        if flow_id:
            flow_ids.add(flow_id)
        source = flow.get("sourceRef")
        target = flow.get("targetRef")
        if source not in nodes:
            errors.append(f"sequenceFlow sourceRef missing node: {source}")
        if target not in nodes:
            errors.append(f"sequenceFlow targetRef missing node: {target}")

    plane = root.find(".//bpmndi:BPMNPlane", BPMN_NS)
    if plane is None:
        errors.append("Missing bpmndi:BPMNPlane")
        return errors, warnings

    shape_refs = {shape.get("bpmnElement") for shape in plane.findall("bpmndi:BPMNShape", BPMN_NS)}
    edge_refs = {edge.get("bpmnElement") for edge in plane.findall("bpmndi:BPMNEdge", BPMN_NS)}

    for required in _required_shape_refs(process, collaboration, lane_set, nodes):
        if required and required not in shape_refs:
            errors.append(f"Missing BPMNShape for: {required}")
    for flow_id in flow_ids:
        if flow_id not in edge_refs:
            errors.append(f"Missing BPMNEdge for sequenceFlow: {flow_id}")

    return errors, warnings


def validate_bpmn_file(path: str | Path) -> Tuple[list[str], list[str]]:
    return validate_bpmn_xml(Path(path).read_text(encoding="utf-8"))


def _required_shape_refs(process, collaboration, lane_set, nodes) -> Iterable[str]:
    if collaboration is not None:
        participant = collaboration.find("bpmn:participant", BPMN_NS)
        if participant is not None:
            yield participant.get("id")
    if lane_set is not None:
        for lane in lane_set.findall("bpmn:lane", BPMN_NS):
            yield lane.get("id")
    for node_id in nodes:
        yield node_id
