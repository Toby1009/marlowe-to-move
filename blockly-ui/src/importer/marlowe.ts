import * as Blockly from 'blockly';

type SpecEnvelope = {
  contract: any;
  extensions?: any;
};

export function loadMarloweSpec(workspace: Blockly.Workspace, payload: unknown) {
  const { contract, extensions } = unwrapPayload(payload);

  Blockly.Events.disable();
  try {
    workspace.clear();

    const contractRoot = createBlock(workspace, 'contract_root');
    contractRoot.moveBy(40, 40);
    connectValue(contractRoot, 'CONTRACT', buildContractBlock(workspace, contract));

    let extensionsRoot: Blockly.Block | null = null;
    if (extensions && (Array.isArray(extensions.oracles) || Array.isArray(extensions.zkp))) {
      extensionsRoot = createBlock(workspace, 'extensions_root');
      extensionsRoot.moveBy(520, 40);

      const oracleBlocks = (extensions.oracles ?? []).map((item: any) =>
        buildOracleRequirementBlock(workspace, item)
      );
      connectStatementStack(extensionsRoot, 'ORACLES', oracleBlocks);

      const zkpBlocks = (extensions.zkp ?? []).map((item: any) =>
        buildZkpRequirementBlock(workspace, item)
      );
      connectStatementStack(extensionsRoot, 'ZKPS', zkpBlocks);
    }

    renderTree(contractRoot);
    if (extensionsRoot) {
      renderTree(extensionsRoot);
    }
  } finally {
    Blockly.Events.enable();
  }
}

function unwrapPayload(payload: unknown): SpecEnvelope {
  if (!isRecord(payload)) {
    throw new Error('Preset JSON must be an object.');
  }
  if ('contract' in payload) {
    const contract = (payload as Record<string, unknown>).contract;
    if (contract === undefined) {
      throw new Error('Preset JSON has a contract wrapper but no contract value.');
    }
    const extensions = isRecord((payload as Record<string, unknown>).extensions)
      ? (payload as Record<string, unknown>).extensions
      : undefined;
    return { contract, extensions };
  }
  return { contract: payload };
}

function buildContractBlock(workspace: Blockly.Workspace, spec: any): Blockly.Block {
  if (spec === 'close') {
    return createBlock(workspace, 'contract_close');
  }
  if (!isRecord(spec)) {
    throw new Error('Unsupported contract node in importer.');
  }

  if ('pay' in spec && 'from_account' in spec && 'to' in spec && 'token' in spec && 'then' in spec) {
    const block = createBlock(workspace, 'contract_pay');
    connectValue(block, 'FROM', buildPartyBlock(workspace, spec.from_account));
    connectValue(block, 'TO', buildPayeeBlock(workspace, spec.to));
    connectValue(block, 'TOKEN', buildTokenBlock(workspace, spec.token));
    connectValue(block, 'VALUE', buildValueBlock(workspace, spec.pay));
    connectValue(block, 'THEN', buildContractBlock(workspace, spec.then));
    return block;
  }

  if ('if' in spec && 'then' in spec && 'else' in spec) {
    const block = createBlock(workspace, 'contract_if');
    connectValue(block, 'COND', buildObservationBlock(workspace, spec.if));
    connectValue(block, 'THEN', buildContractBlock(workspace, spec.then));
    connectValue(block, 'ELSE', buildContractBlock(workspace, spec.else));
    return block;
  }

  if ('when' in spec && 'timeout' in spec && 'timeout_continuation' in spec) {
    const block = createBlock(workspace, 'contract_when');
    block.setFieldValue(String(spec.timeout), 'TIMEOUT');
    const cases = Array.isArray(spec.when) ? spec.when : [];
    const caseBlocks = cases.map((item) => buildCaseBlock(workspace, item));
    connectStatementStack(block, 'CASES', caseBlocks);
    connectValue(block, 'TIMEOUT_CONT', buildContractBlock(workspace, spec.timeout_continuation));
    return block;
  }

  if ('let' in spec && 'be' in spec && 'then' in spec) {
    const block = createBlock(workspace, 'contract_let');
    block.setFieldValue(String(spec.let), 'NAME');
    connectValue(block, 'VALUE', buildValueBlock(workspace, spec.be));
    connectValue(block, 'THEN', buildContractBlock(workspace, spec.then));
    return block;
  }

  if ('assert' in spec && 'then' in spec) {
    const block = createBlock(workspace, 'contract_assert');
    connectValue(block, 'OBS', buildObservationBlock(workspace, spec.assert));
    connectValue(block, 'THEN', buildContractBlock(workspace, spec.then));
    return block;
  }

  throw new Error('Unsupported contract node in importer.');
}

function buildCaseBlock(workspace: Blockly.Workspace, spec: any): Blockly.Block {
  if (!isRecord(spec) || !('case' in spec) || !('then' in spec)) {
    throw new Error('Unsupported case node in importer.');
  }
  const block = createBlock(workspace, 'case_block');
  connectValue(block, 'ACTION', buildActionBlock(workspace, spec.case));
  connectValue(block, 'THEN', buildContractBlock(workspace, spec.then));
  return block;
}

function buildActionBlock(workspace: Blockly.Workspace, spec: any): Blockly.Block {
  if (!isRecord(spec)) {
    throw new Error('Unsupported action node in importer.');
  }

  if ('deposits' in spec && 'party' in spec && 'of_token' in spec && 'into_account' in spec) {
    const block = createBlock(workspace, 'action_deposit');
    connectValue(block, 'PARTY', buildPartyBlock(workspace, spec.party));
    connectValue(block, 'INTO', buildPartyBlock(workspace, spec.into_account));
    connectValue(block, 'TOKEN', buildTokenBlock(workspace, spec.of_token));
    connectValue(block, 'AMOUNT', buildValueBlock(workspace, spec.deposits));
    return block;
  }

  if ('for_choice' in spec && 'choose_between' in spec) {
    const block = createBlock(workspace, 'action_choice');
    connectValue(block, 'CHOICE', buildChoiceIdBlock(workspace, spec.for_choice));
    const bounds = Array.isArray(spec.choose_between) ? spec.choose_between : [];
    const boundBlocks = bounds.map((item) => buildBoundBlock(workspace, item));
    connectStatementStack(block, 'BOUNDS', boundBlocks);
    return block;
  }

  if ('notify_if' in spec) {
    const block = createBlock(workspace, 'action_notify');
    connectValue(block, 'OBS', buildObservationBlock(workspace, spec.notify_if));
    return block;
  }

  throw new Error('Unsupported action node in importer.');
}

function buildBoundBlock(workspace: Blockly.Workspace, spec: any): Blockly.Block {
  if (!isRecord(spec) || !('from' in spec) || !('to' in spec)) {
    throw new Error('Unsupported bound node in importer.');
  }
  const block = createBlock(workspace, 'bound_block');
  block.setFieldValue(String(spec.from), 'FROM');
  block.setFieldValue(String(spec.to), 'TO');
  return block;
}

function buildChoiceIdBlock(workspace: Blockly.Workspace, spec: any): Blockly.Block {
  if (!isRecord(spec) || !('choice_name' in spec) || !('choice_owner' in spec)) {
    throw new Error('Unsupported choice id node in importer.');
  }
  const block = createBlock(workspace, 'choice_id');
  block.setFieldValue(String(spec.choice_name), 'NAME');
  connectValue(block, 'OWNER', buildPartyBlock(workspace, spec.choice_owner));
  return block;
}

function buildPartyBlock(workspace: Blockly.Workspace, spec: any): Blockly.Block {
  if (!isRecord(spec)) {
    throw new Error('Unsupported party node in importer.');
  }
  if ('role_token' in spec) {
    const block = createBlock(workspace, 'party_role');
    block.setFieldValue(String(spec.role_token), 'ROLE');
    return block;
  }
  if ('address' in spec) {
    const block = createBlock(workspace, 'party_address');
    block.setFieldValue(String(spec.address), 'ADDRESS');
    return block;
  }
  throw new Error('Unsupported party node in importer.');
}

function buildPayeeBlock(workspace: Blockly.Workspace, spec: any): Blockly.Block {
  if (!isRecord(spec)) {
    throw new Error('Unsupported payee node in importer.');
  }
  if ('party' in spec) {
    const block = createBlock(workspace, 'payee_party');
    connectValue(block, 'PARTY', buildPartyBlock(workspace, spec.party));
    return block;
  }
  if ('account' in spec) {
    const block = createBlock(workspace, 'payee_account');
    connectValue(block, 'ACCOUNT', buildPartyBlock(workspace, spec.account));
    return block;
  }
  throw new Error('Unsupported payee node in importer.');
}

function buildTokenBlock(workspace: Blockly.Workspace, spec: any): Blockly.Block {
  if (!isRecord(spec) || !('currency_symbol' in spec) || !('token_name' in spec)) {
    throw new Error('Unsupported token node in importer.');
  }
  const block = createBlock(workspace, 'token_block');
  block.setFieldValue(String(spec.currency_symbol), 'CURRENCY');
  block.setFieldValue(String(spec.token_name), 'NAME');
  return block;
}

function buildValueBlock(workspace: Blockly.Workspace, spec: any): Blockly.Block {
  if (typeof spec === 'number') {
    const block = createBlock(workspace, 'value_constant');
    block.setFieldValue(String(spec), 'VALUE');
    return block;
  }
  if (isRecord(spec) && 'constant' in spec) {
    const block = createBlock(workspace, 'value_constant');
    block.setFieldValue(String(spec.constant), 'VALUE');
    return block;
  }
  if (spec === 'time_interval_start') {
    return createBlock(workspace, 'value_time_start');
  }
  if (spec === 'time_interval_end') {
    return createBlock(workspace, 'value_time_end');
  }
  if (!isRecord(spec)) {
    throw new Error('Unsupported value node in importer.');
  }

  if ('amount_of_token' in spec && 'in_account' in spec) {
    const block = createBlock(workspace, 'value_available_money');
    connectValue(block, 'TOKEN', buildTokenBlock(workspace, spec.amount_of_token));
    connectValue(block, 'PARTY', buildPartyBlock(workspace, spec.in_account));
    return block;
  }
  if ('add' in spec && 'and' in spec) {
    const block = createBlock(workspace, 'value_add');
    connectValue(block, 'LHS', buildValueBlock(workspace, spec.add));
    connectValue(block, 'RHS', buildValueBlock(workspace, spec.and));
    return block;
  }
  if ('value' in spec && 'minus' in spec) {
    const block = createBlock(workspace, 'value_sub');
    connectValue(block, 'LHS', buildValueBlock(workspace, spec.value));
    connectValue(block, 'RHS', buildValueBlock(workspace, spec.minus));
    return block;
  }
  if ('times' in spec && 'multiply' in spec) {
    const block = createBlock(workspace, 'value_mul');
    connectValue(block, 'LHS', buildValueBlock(workspace, spec.times));
    connectValue(block, 'RHS', buildValueBlock(workspace, spec.multiply));
    return block;
  }
  if ('divide' in spec && 'by' in spec) {
    const block = createBlock(workspace, 'value_div');
    connectValue(block, 'LHS', buildValueBlock(workspace, spec.divide));
    connectValue(block, 'RHS', buildValueBlock(workspace, spec.by));
    return block;
  }
  if ('value_of_choice' in spec) {
    const block = createBlock(workspace, 'value_choice_value');
    connectValue(block, 'CHOICE', buildChoiceIdBlock(workspace, spec.value_of_choice));
    return block;
  }
  if ('use_value' in spec) {
    const block = createBlock(workspace, 'value_use_value');
    block.setFieldValue(String(spec.use_value), 'NAME');
    return block;
  }
  if ('if' in spec && 'then' in spec && 'else' in spec) {
    const block = createBlock(workspace, 'value_cond');
    connectValue(block, 'OBS', buildObservationBlock(workspace, spec.if));
    connectValue(block, 'THEN', buildValueBlock(workspace, spec.then));
    connectValue(block, 'ELSE', buildValueBlock(workspace, spec.else));
    return block;
  }

  throw new Error('Unsupported value node in importer.');
}

function buildObservationBlock(workspace: Blockly.Workspace, spec: any): Blockly.Block {
  if (spec === true) {
    return createBlock(workspace, 'obs_true');
  }
  if (spec === false) {
    return createBlock(workspace, 'obs_false');
  }
  if (!isRecord(spec)) {
    throw new Error('Unsupported observation node in importer.');
  }

  if ('both' in spec && 'and' in spec) {
    const block = createBlock(workspace, 'obs_and');
    connectValue(block, 'LHS', buildObservationBlock(workspace, spec.both));
    connectValue(block, 'RHS', buildObservationBlock(workspace, spec.and));
    return block;
  }
  if ('either' in spec && 'or' in spec) {
    const block = createBlock(workspace, 'obs_or');
    connectValue(block, 'LHS', buildObservationBlock(workspace, spec.either));
    connectValue(block, 'RHS', buildObservationBlock(workspace, spec.or));
    return block;
  }
  if ('not' in spec) {
    const block = createBlock(workspace, 'obs_not');
    connectValue(block, 'OBS', buildObservationBlock(workspace, spec.not));
    return block;
  }
  if ('chose_something_for' in spec) {
    const block = createBlock(workspace, 'obs_chose_something');
    connectValue(block, 'CHOICE', buildChoiceIdBlock(workspace, spec.chose_something_for));
    return block;
  }
  if ('value' in spec && 'ge_than' in spec) {
    const block = createBlock(workspace, 'obs_ge');
    connectValue(block, 'LHS', buildValueBlock(workspace, spec.value));
    connectValue(block, 'RHS', buildValueBlock(workspace, spec.ge_than));
    return block;
  }
  if ('value' in spec && 'gt' in spec) {
    const block = createBlock(workspace, 'obs_gt');
    connectValue(block, 'LHS', buildValueBlock(workspace, spec.value));
    connectValue(block, 'RHS', buildValueBlock(workspace, spec.gt));
    return block;
  }
  if ('value' in spec && 'lt' in spec) {
    const block = createBlock(workspace, 'obs_lt');
    connectValue(block, 'LHS', buildValueBlock(workspace, spec.value));
    connectValue(block, 'RHS', buildValueBlock(workspace, spec.lt));
    return block;
  }
  if ('value' in spec && 'le_than' in spec) {
    const block = createBlock(workspace, 'obs_le');
    connectValue(block, 'LHS', buildValueBlock(workspace, spec.value));
    connectValue(block, 'RHS', buildValueBlock(workspace, spec.le_than));
    return block;
  }
  if ('value' in spec && 'equal_to' in spec) {
    const block = createBlock(workspace, 'obs_eq');
    connectValue(block, 'LHS', buildValueBlock(workspace, spec.value));
    connectValue(block, 'RHS', buildValueBlock(workspace, spec.equal_to));
    return block;
  }

  throw new Error('Unsupported observation node in importer.');
}

function buildOracleRequirementBlock(workspace: Blockly.Workspace, spec: any): Blockly.Block {
  if (!isRecord(spec)) {
    throw new Error('Unsupported Oracle extension in importer.');
  }
  const block = createBlock(workspace, 'ext_oracle_requirement');
  setFieldIfPresent(block, 'ID', spec.id);
  setFieldIfPresent(block, 'TYPE', spec.type);
  setFieldIfPresent(block, 'DESCRIPTION', spec.description);
  if (isRecord(spec.inputs)) {
    setFieldIfPresent(block, 'PAIR', spec.inputs.pair);
    setFieldIfPresent(block, 'FEED_KEY', spec.inputs.feed_key);
    setFieldIfPresent(block, 'TIMESTAMP', spec.inputs.timestamp);
    setFieldIfPresent(block, 'MAX_STALENESS_SEC', spec.inputs.max_staleness_sec);
    setFieldIfPresent(block, 'SOURCE_CHAIN', spec.inputs.source_chain);
  }
  if (isRecord(spec.integrity)) {
    setFieldIfPresent(block, 'SIGNED_BY', joinCsv(spec.integrity.signed_by));
    setFieldIfPresent(block, 'SIGNATURE_SCHEME', spec.integrity.signature_scheme);
    setFieldIfPresent(block, 'REQUIRED_QUORUM', spec.integrity.required_quorum);
  }
  if (isRecord(spec.bind_to)) {
    setFieldIfPresent(block, 'BIND_KIND', spec.bind_to.kind);
    setFieldIfPresent(block, 'BIND_NAME', spec.bind_to.name);
  }
  return block;
}

function buildZkpRequirementBlock(workspace: Blockly.Workspace, spec: any): Blockly.Block {
  if (!isRecord(spec)) {
    throw new Error('Unsupported ZKP extension in importer.');
  }
  const block = createBlock(workspace, 'ext_zkp_requirement');
  setFieldIfPresent(block, 'ID', spec.id);
  setFieldIfPresent(block, 'PROOF_SYSTEM', spec.proof_system);
  setFieldIfPresent(block, 'STATEMENT', spec.statement);
  setFieldIfPresent(block, 'PUBLIC_INPUTS', joinCsv(spec.public_inputs));
  if (isRecord(spec.verifier)) {
    setFieldIfPresent(block, 'VERIFIER_CHAIN', spec.verifier.chain);
    setFieldIfPresent(block, 'VERIFIER_MODULE', spec.verifier.module);
    setFieldIfPresent(block, 'VERIFIER_FUNCTION', spec.verifier.function);
  }
  if (isRecord(spec.bind_to)) {
    setFieldIfPresent(block, 'BIND_KIND', spec.bind_to.kind);
    setFieldIfPresent(block, 'BIND_NAME', spec.bind_to.name);
  }
  if (isRecord(spec.privacy)) {
    setFieldIfPresent(block, 'REVEALS', joinCsv(spec.privacy.reveals));
    setFieldIfPresent(block, 'HIDES', joinCsv(spec.privacy.hides));
  }
  return block;
}

function createBlock(workspace: Blockly.Workspace, type: string): Blockly.Block {
  const block = workspace.newBlock(type);
  const rendered = block as Blockly.Block & { initSvg?: () => void };
  rendered.initSvg?.();
  return block;
}

function connectValue(parent: Blockly.Block, inputName: string, child: Blockly.Block) {
  const connection = parent.getInput(inputName)?.connection;
  if (!connection || !child.outputConnection) {
    throw new Error(`Cannot connect value input ${inputName} on ${parent.type}.`);
  }
  connection.connect(child.outputConnection);
}

function connectStatementStack(parent: Blockly.Block, inputName: string, blocks: Blockly.Block[]) {
  if (blocks.length === 0) {
    return;
  }
  const connection = parent.getInput(inputName)?.connection;
  if (!connection || !blocks[0].previousConnection) {
    throw new Error(`Cannot connect statement input ${inputName} on ${parent.type}.`);
  }
  connection.connect(blocks[0].previousConnection);
  for (let i = 0; i < blocks.length - 1; i += 1) {
    const current = blocks[i];
    const next = blocks[i + 1];
    if (!current.nextConnection || !next.previousConnection) {
      throw new Error(`Cannot chain statements for ${current.type}.`);
    }
    current.nextConnection.connect(next.previousConnection);
  }
}

function renderTree(root: Blockly.Block) {
  const descendants = root.getDescendants(false);
  for (const block of descendants) {
    const rendered = block as Blockly.Block & { render?: () => void };
    rendered.render?.();
  }
}

function joinCsv(value: unknown): string {
  if (!Array.isArray(value)) {
    return '';
  }
  return value.map((item) => String(item)).join(',');
}

function setFieldIfPresent(block: Blockly.Block, field: string, value: unknown) {
  if (value === undefined || value === null) {
    return;
  }
  block.setFieldValue(String(value), field);
}

function isRecord(value: unknown): value is Record<string, any> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
