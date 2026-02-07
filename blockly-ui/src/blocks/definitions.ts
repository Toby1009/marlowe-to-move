import * as Blockly from 'blockly';

type BlockJson = Blockly.BlockDefinition;

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
    message0: 'When cases %1 timeout %2 timeout continuation %3',
    args0: [
      { type: 'input_statement', name: 'CASES', check: 'Case' },
      { type: 'field_number', name: 'TIMEOUT', value: 0 },
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
      { type: 'field_number', name: 'FROM', value: 0 },
      { type: 'field_number', name: 'TO', value: 0 },
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
      { type: 'field_number', name: 'VALUE', value: 0 },
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

export function registerBlocks() {
  Blockly.defineBlocksWithJsonArray(blocks);
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
        { kind: 'block', type: 'value_negate' },
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
  ],
};
