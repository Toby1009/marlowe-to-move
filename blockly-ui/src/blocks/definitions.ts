import * as Blockly from 'blockly';

type BlockJson = Blockly.BlockDefinition;
type DropdownOption = [string, string];

const MISSING_BIND_TARGET_VALUE = '__missing_bind_target__';

const blocks: BlockJson[] = [
  {
    type: 'contract_root',
    message0: 'Contract Root %1',
    args0: [
      { type: 'input_value', name: 'CONTRACT', check: 'Contract' }
    ],
    colour: 290,
    tooltip: 'Root container for a Marlowe contract',
  },
  {
    type: 'extensions_root',
    message0: 'Extensions Root',
    message1: 'Oracle extensions %1',
    args1: [
      { type: 'input_statement', name: 'ORACLES', check: 'OracleRequirement' }
    ],
    message2: 'ZKP extensions %1',
    args2: [
      { type: 'input_statement', name: 'ZKPS', check: 'ZkpRequirement' }
    ],
    colour: 20,
    tooltip: 'Optional top-level platform extensions for Oracle and ZKP requirements',
  },
  {
    type: 'contract_close',
    message0: 'Close',
    output: 'Contract',
    colour: 290,
  },
  {
    type: 'contract_pay',
    message0: 'Pay from %1 to %2 token %3 value %4 then %5',
    args0: [
      { type: 'input_value', name: 'FROM', check: 'Party' },
      { type: 'input_value', name: 'TO', check: 'Payee' },
      { type: 'input_value', name: 'TOKEN', check: 'Token' },
      { type: 'input_value', name: 'VALUE', check: 'Value' },
      { type: 'input_value', name: 'THEN', check: 'Contract' },
    ],
    output: 'Contract',
    colour: 290,
  },
  {
    type: 'contract_if',
    message0: 'If %1 then %2 else %3',
    args0: [
      { type: 'input_value', name: 'COND', check: 'Observation' },
      { type: 'input_value', name: 'THEN', check: 'Contract' },
      { type: 'input_value', name: 'ELSE', check: 'Contract' },
    ],
    output: 'Contract',
    colour: 290,
  },
  {
    type: 'contract_when',
    message0: 'When cases %1 timeout (Unix ms) %2 timeout continuation %3',
    args0: [
      { type: 'input_statement', name: 'CASES', check: 'Case' },
      { type: 'field_number', name: 'TIMEOUT', value: 1775174399000, min: 946684800000, precision: 1 },
      { type: 'input_value', name: 'TIMEOUT_CONT', check: 'Contract' },
    ],
    output: 'Contract',
    colour: 290,
  },
  {
    type: 'contract_let',
    message0: 'Let %1 be %2 then %3',
    args0: [
      { type: 'field_input', name: 'NAME', text: 'value_id' },
      { type: 'input_value', name: 'VALUE', check: 'Value' },
      { type: 'input_value', name: 'THEN', check: 'Contract' },
    ],
    output: 'Contract',
    colour: 290,
  },
  {
    type: 'contract_assert',
    message0: 'Assert %1 then %2',
    args0: [
      { type: 'input_value', name: 'OBS', check: 'Observation' },
      { type: 'input_value', name: 'THEN', check: 'Contract' },
    ],
    output: 'Contract',
    colour: 290,
  },
  {
    type: 'case_block',
    message0: 'Case %1 then %2',
    args0: [
      { type: 'input_value', name: 'ACTION', check: 'Action' },
      { type: 'input_value', name: 'THEN', check: 'Contract' },
    ],
    previousStatement: 'Case',
    nextStatement: 'Case',
    colour: 30,
  },
  {
    type: 'action_deposit',
    message0: 'Deposit by %1 into %2 token %3 amount %4',
    args0: [
      { type: 'input_value', name: 'PARTY', check: 'Party' },
      { type: 'input_value', name: 'INTO', check: 'Party' },
      { type: 'input_value', name: 'TOKEN', check: 'Token' },
      { type: 'input_value', name: 'AMOUNT', check: 'Value' },
    ],
    output: 'Action',
    colour: 30,
  },
  {
    type: 'action_choice',
    message0: 'Choice %1 bounds %2',
    args0: [
      { type: 'input_value', name: 'CHOICE', check: 'ChoiceId' },
      { type: 'input_statement', name: 'BOUNDS', check: 'Bound' },
    ],
    output: 'Action',
    colour: 30,
  },
  {
    type: 'action_notify',
    message0: 'Notify if %1',
    args0: [
      { type: 'input_value', name: 'OBS', check: 'Observation' },
    ],
    output: 'Action',
    colour: 30,
  },
  {
    type: 'bound_block',
    message0: 'Bound from %1 to %2',
    args0: [
      { type: 'field_number', name: 'FROM', value: 0, min: 0, precision: 1 },
      { type: 'field_number', name: 'TO', value: 0, min: 0, precision: 1 },
    ],
    previousStatement: 'Bound',
    nextStatement: 'Bound',
    colour: 60,
  },
  {
    type: 'choice_id',
    message0: 'ChoiceId name %1 owner %2',
    args0: [
      { type: 'field_input', name: 'NAME', text: 'choice_name' },
      { type: 'input_value', name: 'OWNER', check: 'Party' },
    ],
    output: 'ChoiceId',
    colour: 60,
  },
  {
    type: 'party_role',
    message0: 'Role %1',
    args0: [
      { type: 'field_input', name: 'ROLE', text: 'RoleToken' },
    ],
    output: 'Party',
    colour: 120,
  },
  {
    type: 'party_address',
    message0: 'Address %1',
    args0: [
      { type: 'field_input', name: 'ADDRESS', text: '0x...' },
    ],
    output: 'Party',
    colour: 120,
  },
  {
    type: 'payee_party',
    message0: 'Payee party %1',
    args0: [
      { type: 'input_value', name: 'PARTY', check: 'Party' },
    ],
    output: 'Payee',
    colour: 120,
  },
  {
    type: 'payee_account',
    message0: 'Payee account %1',
    args0: [
      { type: 'input_value', name: 'ACCOUNT', check: 'Party' },
    ],
    output: 'Payee',
    colour: 120,
  },
  {
    type: 'token_block',
    message0: 'Token currency_symbol %1 token_name %2',
    args0: [
      { type: 'field_input', name: 'CURRENCY', text: '' },
      { type: 'field_input', name: 'NAME', text: '' },
    ],
    output: 'Token',
    colour: 160,
  },
  {
    type: 'value_constant',
    message0: 'Constant %1',
    args0: [
      { type: 'field_number', name: 'VALUE', value: 0, min: 0, precision: 1 },
    ],
    output: 'Value',
    colour: 210,
  },
  {
    type: 'value_available_money',
    message0: 'Available money token %1 in account %2',
    args0: [
      { type: 'input_value', name: 'TOKEN', check: 'Token' },
      { type: 'input_value', name: 'PARTY', check: 'Party' },
    ],
    output: 'Value',
    colour: 210,
  },
  {
    type: 'value_add',
    message0: 'Add %1 and %2',
    args0: [
      { type: 'input_value', name: 'LHS', check: 'Value' },
      { type: 'input_value', name: 'RHS', check: 'Value' },
    ],
    output: 'Value',
    colour: 210,
  },
  {
    type: 'value_sub',
    message0: 'Subtract %1 minus %2',
    args0: [
      { type: 'input_value', name: 'LHS', check: 'Value' },
      { type: 'input_value', name: 'RHS', check: 'Value' },
    ],
    output: 'Value',
    colour: 210,
  },
  {
    type: 'value_mul',
    message0: 'Multiply %1 times %2',
    args0: [
      { type: 'input_value', name: 'LHS', check: 'Value' },
      { type: 'input_value', name: 'RHS', check: 'Value' },
    ],
    output: 'Value',
    colour: 210,
  },
  {
    type: 'value_div',
    message0: 'Divide %1 by %2',
    args0: [
      { type: 'input_value', name: 'LHS', check: 'Value' },
      { type: 'input_value', name: 'RHS', check: 'Value' },
    ],
    output: 'Value',
    colour: 210,
  },
  {
    type: 'value_negate',
    message0: 'Negate %1',
    args0: [
      { type: 'input_value', name: 'VALUE', check: 'Value' },
    ],
    output: 'Value',
    colour: 210,
  },
  {
    type: 'value_choice_value',
    message0: 'Choice value %1',
    args0: [
      { type: 'input_value', name: 'CHOICE', check: 'ChoiceId' },
    ],
    output: 'Value',
    colour: 210,
  },
  {
    type: 'value_time_start',
    message0: 'Time interval start',
    output: 'Value',
    colour: 210,
  },
  {
    type: 'value_time_end',
    message0: 'Time interval end',
    output: 'Value',
    colour: 210,
  },
  {
    type: 'value_use_value',
    message0: 'Use value %1',
    args0: [
      { type: 'field_input', name: 'NAME', text: 'value_id' },
    ],
    output: 'Value',
    colour: 210,
  },
  {
    type: 'value_cond',
    message0: 'If %1 then value %2 else value %3',
    args0: [
      { type: 'input_value', name: 'OBS', check: 'Observation' },
      { type: 'input_value', name: 'THEN', check: 'Value' },
      { type: 'input_value', name: 'ELSE', check: 'Value' },
    ],
    output: 'Value',
    colour: 210,
  },
  {
    type: 'obs_true',
    message0: 'True',
    output: 'Observation',
    colour: 260,
  },
  {
    type: 'obs_false',
    message0: 'False',
    output: 'Observation',
    colour: 260,
  },
  {
    type: 'obs_and',
    message0: 'And %1 and %2',
    args0: [
      { type: 'input_value', name: 'LHS', check: 'Observation' },
      { type: 'input_value', name: 'RHS', check: 'Observation' },
    ],
    output: 'Observation',
    colour: 260,
  },
  {
    type: 'obs_or',
    message0: 'Or %1 or %2',
    args0: [
      { type: 'input_value', name: 'LHS', check: 'Observation' },
      { type: 'input_value', name: 'RHS', check: 'Observation' },
    ],
    output: 'Observation',
    colour: 260,
  },
  {
    type: 'obs_not',
    message0: 'Not %1',
    args0: [
      { type: 'input_value', name: 'OBS', check: 'Observation' },
    ],
    output: 'Observation',
    colour: 260,
  },
  {
    type: 'obs_chose_something',
    message0: 'Chose something for %1',
    args0: [
      { type: 'input_value', name: 'CHOICE', check: 'ChoiceId' },
    ],
    output: 'Observation',
    colour: 260,
  },
  {
    type: 'obs_ge',
    message0: 'Value %1 >= %2',
    args0: [
      { type: 'input_value', name: 'LHS', check: 'Value' },
      { type: 'input_value', name: 'RHS', check: 'Value' },
    ],
    output: 'Observation',
    colour: 260,
  },
  {
    type: 'obs_gt',
    message0: 'Value %1 > %2',
    args0: [
      { type: 'input_value', name: 'LHS', check: 'Value' },
      { type: 'input_value', name: 'RHS', check: 'Value' },
    ],
    output: 'Observation',
    colour: 260,
  },
  {
    type: 'obs_lt',
    message0: 'Value %1 < %2',
    args0: [
      { type: 'input_value', name: 'LHS', check: 'Value' },
      { type: 'input_value', name: 'RHS', check: 'Value' },
    ],
    output: 'Observation',
    colour: 260,
  },
  {
    type: 'obs_le',
    message0: 'Value %1 <= %2',
    args0: [
      { type: 'input_value', name: 'LHS', check: 'Value' },
      { type: 'input_value', name: 'RHS', check: 'Value' },
    ],
    output: 'Observation',
    colour: 260,
  },
  {
    type: 'obs_eq',
    message0: 'Value %1 = %2',
    args0: [
      { type: 'input_value', name: 'LHS', check: 'Value' },
      { type: 'input_value', name: 'RHS', check: 'Value' },
    ],
    output: 'Observation',
    colour: 260,
  },
];

function getChoiceBindOptions(sourceBlock?: Blockly.Block | null): DropdownOption[] {
  const workspace = sourceBlock?.workspace;
  if (!workspace) {
    return [['Define ChoiceId in Contract Root first', MISSING_BIND_TARGET_VALUE]];
  }

  const names = new Set<string>();
  for (const block of workspace.getAllBlocks(false)) {
    if (block.type !== 'choice_id') {
      continue;
    }
    const name = String(block.getFieldValue('NAME') ?? '').trim();
    if (name) {
      names.add(name);
    }
  }

  const options = Array.from(names)
    .sort((lhs, rhs) => lhs.localeCompare(rhs))
    .map((name): DropdownOption => [name, name]);

  if (options.length === 0) {
    return [['Define ChoiceId in Contract Root first', MISSING_BIND_TARGET_VALUE]];
  }
  return options;
}

function bindNameDropdown() {
  return new Blockly.FieldDropdown(function (this: Blockly.FieldDropdown) {
    const options = getChoiceBindOptions(this.getSourceBlock());
    const currentValue = String(this.getValue() ?? '').trim();
    if (
      currentValue &&
      currentValue !== MISSING_BIND_TARGET_VALUE &&
      !options.some(([, value]) => value === currentValue)
    ) {
      return [[currentValue, currentValue], ...options];
    }
    return options;
  });
}

function registerExtensionBlocks() {
  Blockly.Blocks.ext_oracle_requirement = {
    init() {
      this.appendDummyInput()
        .appendField('Oracle requirement');
      this.appendDummyInput()
        .appendField('id')
        .appendField(new Blockly.FieldTextInput('fx_usdc_twd'), 'ID')
        .appendField('type')
        .appendField(
          new Blockly.FieldDropdown([
            ['price_feed', 'price_feed'],
            ['attestation', 'attestation'],
            ['cross_chain_message', 'cross_chain_message'],
            ['custom', 'custom'],
          ]),
          'TYPE'
        );
      this.appendDummyInput()
        .appendField('description')
        .appendField(new Blockly.FieldTextInput('USDC/TWD exchange rate'), 'DESCRIPTION');
      this.appendDummyInput()
        .appendField('pair')
        .appendField(new Blockly.FieldTextInput('USDC/TWD'), 'PAIR')
        .appendField('feed key')
        .appendField(new Blockly.FieldTextInput('chainlink.fx.usdc_twd'), 'FEED_KEY');
      this.appendDummyInput()
        .appendField('timestamp')
        .appendField(new Blockly.FieldTextInput('tx_time'), 'TIMESTAMP')
        .appendField('max staleness sec')
        .appendField(new Blockly.FieldNumber(3600, 0, undefined, 1), 'MAX_STALENESS_SEC');
      this.appendDummyInput()
        .appendField('source chain')
        .appendField(new Blockly.FieldTextInput('ethereum'), 'SOURCE_CHAIN');
      this.appendDummyInput()
        .appendField('signed by')
        .appendField(new Blockly.FieldTextInput('OracleProviderA'), 'SIGNED_BY')
        .appendField('scheme')
        .appendField(new Blockly.FieldTextInput('ed25519'), 'SIGNATURE_SCHEME')
        .appendField('quorum')
        .appendField(new Blockly.FieldNumber(1, 1, undefined, 1), 'REQUIRED_QUORUM');
      this.appendDummyInput()
        .appendField('bind kind')
        .appendField(
          new Blockly.FieldDropdown([
            ['choice', 'choice'],
            ['observation', 'observation'],
            ['choice_or_notify', 'choice_or_notify'],
          ]),
          'BIND_KIND'
        )
        .appendField('bind name')
        .appendField(bindNameDropdown(), 'BIND_NAME');
      this.setPreviousStatement(true, 'OracleRequirement');
      this.setNextStatement(true, 'OracleRequirement');
      this.setColour(15);
      this.setTooltip('Platform-level Oracle requirement bound to a contract ChoiceId name.');
    },
  };

  Blockly.Blocks.ext_zkp_requirement = {
    init() {
      this.appendDummyInput()
        .appendField('ZKP requirement');
      this.appendDummyInput()
        .appendField('id')
        .appendField(new Blockly.FieldTextInput('eligibility_proof'), 'ID')
        .appendField('proof system')
        .appendField(
          new Blockly.FieldDropdown([
            ['groth16', 'groth16'],
            ['plonk', 'plonk'],
            ['halo2', 'halo2'],
            ['custom', 'custom'],
          ]),
          'PROOF_SYSTEM'
        );
      this.appendDummyInput()
        .appendField('statement')
        .appendField(new Blockly.FieldTextInput('Applicant is eligible for the grant'), 'STATEMENT');
      this.appendDummyInput()
        .appendField('public inputs')
        .appendField(new Blockly.FieldTextInput('applicant_id_hash,policy_id'), 'PUBLIC_INPUTS');
      this.appendDummyInput()
        .appendField('verifier chain')
        .appendField(new Blockly.FieldTextInput('sui'), 'VERIFIER_CHAIN')
        .appendField('module')
        .appendField(new Blockly.FieldTextInput('zk_verifier'), 'VERIFIER_MODULE')
        .appendField('function')
        .appendField(new Blockly.FieldTextInput('verify_eligibility'), 'VERIFIER_FUNCTION');
      this.appendDummyInput()
        .appendField('bind kind')
        .appendField(
          new Blockly.FieldDropdown([
            ['choice', 'choice'],
            ['choice_or_notify', 'choice_or_notify'],
            ['observation', 'observation'],
          ]),
          'BIND_KIND'
        )
        .appendField('bind name')
        .appendField(bindNameDropdown(), 'BIND_NAME');
      this.appendDummyInput()
        .appendField('reveals')
        .appendField(new Blockly.FieldTextInput('eligible_only'), 'REVEALS')
        .appendField('hides')
        .appendField(new Blockly.FieldTextInput('income,full_identity'), 'HIDES');
      this.setPreviousStatement(true, 'ZkpRequirement');
      this.setNextStatement(true, 'ZkpRequirement');
      this.setColour(330);
      this.setTooltip('Platform-level ZKP requirement bound to a contract ChoiceId name.');
    },
  };
}

export function registerBlocks() {
  Blockly.defineBlocksWithJsonArray(blocks);
  registerExtensionBlocks();
}

export const toolbox = {
  kind: 'categoryToolbox',
  contents: [
    {
      kind: 'category',
      name: 'Root',
      colour: 290,
      contents: [
        { kind: 'block', type: 'contract_root' },
        { kind: 'block', type: 'extensions_root' },
      ],
    },
    {
      kind: 'category',
      name: 'Contract',
      colour: 290,
      contents: [
        { kind: 'block', type: 'contract_close' },
        { kind: 'block', type: 'contract_pay' },
        { kind: 'block', type: 'contract_if' },
        { kind: 'block', type: 'contract_when' },
        { kind: 'block', type: 'contract_let' },
        { kind: 'block', type: 'contract_assert' },
      ],
    },
    {
      kind: 'category',
      name: 'Case & Action',
      colour: 30,
      contents: [
        { kind: 'block', type: 'case_block' },
        { kind: 'block', type: 'action_deposit' },
        { kind: 'block', type: 'action_choice' },
        { kind: 'block', type: 'action_notify' },
        { kind: 'block', type: 'bound_block' },
        { kind: 'block', type: 'choice_id' },
      ],
    },
    {
      kind: 'category',
      name: 'Party & Token',
      colour: 120,
      contents: [
        { kind: 'block', type: 'party_role' },
        { kind: 'block', type: 'party_address' },
        { kind: 'block', type: 'payee_party' },
        { kind: 'block', type: 'payee_account' },
        { kind: 'block', type: 'token_block' },
      ],
    },
    {
      kind: 'category',
      name: 'Value',
      colour: 210,
      contents: [
        { kind: 'block', type: 'value_constant' },
        { kind: 'block', type: 'value_available_money' },
        { kind: 'block', type: 'value_add' },
        { kind: 'block', type: 'value_sub' },
        { kind: 'block', type: 'value_mul' },
        { kind: 'block', type: 'value_div' },
        { kind: 'block', type: 'value_choice_value' },
        { kind: 'block', type: 'value_time_start' },
        { kind: 'block', type: 'value_time_end' },
        { kind: 'block', type: 'value_use_value' },
        { kind: 'block', type: 'value_cond' },
      ],
    },
    {
      kind: 'category',
      name: 'Observation',
      colour: 260,
      contents: [
        { kind: 'block', type: 'obs_true' },
        { kind: 'block', type: 'obs_false' },
        { kind: 'block', type: 'obs_and' },
        { kind: 'block', type: 'obs_or' },
        { kind: 'block', type: 'obs_not' },
        { kind: 'block', type: 'obs_chose_something' },
        { kind: 'block', type: 'obs_ge' },
        { kind: 'block', type: 'obs_gt' },
        { kind: 'block', type: 'obs_lt' },
        { kind: 'block', type: 'obs_le' },
        { kind: 'block', type: 'obs_eq' },
      ],
    },
    {
      kind: 'category',
      name: 'Extensions',
      colour: 15,
      contents: [
        { kind: 'block', type: 'ext_oracle_requirement' },
        { kind: 'block', type: 'ext_zkp_requirement' },
      ],
    },
  ],
};
