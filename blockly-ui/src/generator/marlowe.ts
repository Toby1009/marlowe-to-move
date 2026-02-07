import * as Blockly from 'blockly';

function requireInput(block: Blockly.Block, name: string): Blockly.Block {
  const target = block.getInputTargetBlock(name);
  if (!target) {
    throw new Error(`Missing required input \"${name}\" on ${block.type}`);
  }
  return target;
}

function collectStack(start: Blockly.Block | null): Blockly.Block[] {
  const out: Blockly.Block[] = [];
  let current = start;
  while (current) {
    out.push(current);
    current = current.getNextBlock();
  }
  return out;
}

export function buildMarloweSpec(workspace: Blockly.Workspace): any {
  const root = workspace.getTopBlocks(false).find((b) => b.type === 'contract_root');
  if (!root) {
    throw new Error('Please add a Contract Root block.');
  }
  const contract = root.getInputTargetBlock('CONTRACT');
  if (!contract) {
    throw new Error('Contract Root must contain a Contract block.');
  }
  return buildContract(contract);
}

function buildContract(block: Blockly.Block): any {
  switch (block.type) {
    case 'contract_close':
      return 'close';
    case 'contract_pay':
      return {
        from_account: buildParty(requireInput(block, 'FROM')),
        to: buildPayee(requireInput(block, 'TO')),
        token: buildToken(requireInput(block, 'TOKEN')),
        pay: buildValue(requireInput(block, 'VALUE')),
        then: buildContract(requireInput(block, 'THEN')),
      };
    case 'contract_if':
      return {
        if: buildObservation(requireInput(block, 'COND')),
        then: buildContract(requireInput(block, 'THEN')),
        else: buildContract(requireInput(block, 'ELSE')),
      };
    case 'contract_when': {
      const caseBlocks = collectStack(block.getInputTargetBlock('CASES'));
      const cases = caseBlocks.map((caseBlock) => buildCase(caseBlock));
      return {
        when: cases,
        timeout: Number(block.getFieldValue('TIMEOUT')),
        timeout_continuation: buildContract(requireInput(block, 'TIMEOUT_CONT')),
      };
    }
    case 'contract_let':
      return {
        let: block.getFieldValue('NAME'),
        be: buildValue(requireInput(block, 'VALUE')),
        then: buildContract(requireInput(block, 'THEN')),
      };
    case 'contract_assert':
      return {
        assert: buildObservation(requireInput(block, 'OBS')),
        then: buildContract(requireInput(block, 'THEN')),
      };
    default:
      throw new Error(`Unsupported contract block: ${block.type}`);
  }
}

function buildCase(block: Blockly.Block): any {
  if (block.type !== 'case_block') {
    throw new Error(`Expected case_block, got ${block.type}`);
  }
  return {
    case: buildAction(requireInput(block, 'ACTION')),
    then: buildContract(requireInput(block, 'THEN')),
  };
}

function buildAction(block: Blockly.Block): any {
  switch (block.type) {
    case 'action_deposit':
      return {
        party: buildParty(requireInput(block, 'PARTY')),
        of_token: buildToken(requireInput(block, 'TOKEN')),
        into_account: buildParty(requireInput(block, 'INTO')),
        deposits: buildValue(requireInput(block, 'AMOUNT')),
      };
    case 'action_choice': {
      const boundsBlocks = collectStack(block.getInputTargetBlock('BOUNDS'));
      return {
        for_choice: buildChoiceId(requireInput(block, 'CHOICE')),
        choose_between: boundsBlocks.map((b) => buildBound(b)),
      };
    }
    case 'action_notify':
      return {
        notify_if: buildObservation(requireInput(block, 'OBS')),
      };
    default:
      throw new Error(`Unsupported action block: ${block.type}`);
  }
}

function buildBound(block: Blockly.Block): any {
  if (block.type !== 'bound_block') {
    throw new Error(`Expected bound_block, got ${block.type}`);
  }
  return {
    from: Number(block.getFieldValue('FROM')),
    to: Number(block.getFieldValue('TO')),
  };
}

function buildChoiceId(block: Blockly.Block): any {
  if (block.type !== 'choice_id') {
    throw new Error(`Expected choice_id, got ${block.type}`);
  }
  return {
    choice_name: block.getFieldValue('NAME'),
    choice_owner: buildParty(requireInput(block, 'OWNER')),
  };
}

function buildParty(block: Blockly.Block): any {
  switch (block.type) {
    case 'party_role':
      return { role_token: block.getFieldValue('ROLE') };
    case 'party_address':
      return { address: block.getFieldValue('ADDRESS') };
    default:
      throw new Error(`Unsupported party block: ${block.type}`);
  }
}

function buildPayee(block: Blockly.Block): any {
  switch (block.type) {
    case 'payee_party':
      return { party: buildParty(requireInput(block, 'PARTY')) };
    case 'payee_account':
      return { account: buildParty(requireInput(block, 'ACCOUNT')) };
    default:
      throw new Error(`Unsupported payee block: ${block.type}`);
  }
}

function buildToken(block: Blockly.Block): any {
  if (block.type !== 'token_block') {
    throw new Error(`Expected token_block, got ${block.type}`);
  }
  return {
    currency_symbol: block.getFieldValue('CURRENCY'),
    token_name: block.getFieldValue('NAME'),
  };
}

function buildValue(block: Blockly.Block): any {
  switch (block.type) {
    case 'value_constant':
      return Number(block.getFieldValue('VALUE'));
    case 'value_available_money':
      return {
        amount_of_token: buildToken(requireInput(block, 'TOKEN')),
        in_account: buildParty(requireInput(block, 'PARTY')),
      };
    case 'value_add':
      return {
        add: buildValue(requireInput(block, 'LHS')),
        and: buildValue(requireInput(block, 'RHS')),
      };
    case 'value_sub':
      return {
        value: buildValue(requireInput(block, 'LHS')),
        minus: buildValue(requireInput(block, 'RHS')),
      };
    case 'value_mul':
      return {
        times: buildValue(requireInput(block, 'LHS')),
        multiply: buildValue(requireInput(block, 'RHS')),
      };
    case 'value_div':
      return {
        divide: buildValue(requireInput(block, 'LHS')),
        by: buildValue(requireInput(block, 'RHS')),
      };
    case 'value_negate':
      return {
        negate: buildValue(requireInput(block, 'VALUE')),
      };
    case 'value_choice_value':
      return {
        value_of_choice: buildChoiceId(requireInput(block, 'CHOICE')),
      };
    case 'value_time_start':
      return 'time_interval_start';
    case 'value_time_end':
      return 'time_interval_end';
    case 'value_use_value':
      return { use_value: block.getFieldValue('NAME') };
    case 'value_cond':
      return {
        if: buildObservation(requireInput(block, 'OBS')),
        then: buildValue(requireInput(block, 'THEN')),
        else: buildValue(requireInput(block, 'ELSE')),
      };
    default:
      throw new Error(`Unsupported value block: ${block.type}`);
  }
}

function buildObservation(block: Blockly.Block): any {
  switch (block.type) {
    case 'obs_true':
      return true;
    case 'obs_false':
      return false;
    case 'obs_and':
      return {
        both: buildObservation(requireInput(block, 'LHS')),
        and: buildObservation(requireInput(block, 'RHS')),
      };
    case 'obs_or':
      return {
        either: buildObservation(requireInput(block, 'LHS')),
        or: buildObservation(requireInput(block, 'RHS')),
      };
    case 'obs_not':
      return {
        not: buildObservation(requireInput(block, 'OBS')),
      };
    case 'obs_chose_something':
      return {
        chose_something_for: buildChoiceId(requireInput(block, 'CHOICE')),
      };
    case 'obs_ge':
      return {
        value: buildValue(requireInput(block, 'LHS')),
        ge_than: buildValue(requireInput(block, 'RHS')),
      };
    case 'obs_gt':
      return {
        value: buildValue(requireInput(block, 'LHS')),
        gt: buildValue(requireInput(block, 'RHS')),
      };
    case 'obs_lt':
      return {
        value: buildValue(requireInput(block, 'LHS')),
        lt: buildValue(requireInput(block, 'RHS')),
      };
    case 'obs_le':
      return {
        value: buildValue(requireInput(block, 'LHS')),
        le_than: buildValue(requireInput(block, 'RHS')),
      };
    case 'obs_eq':
      return {
        value: buildValue(requireInput(block, 'LHS')),
        equal_to: buildValue(requireInput(block, 'RHS')),
      };
    default:
      throw new Error(`Unsupported observation block: ${block.type}`);
  }
}
