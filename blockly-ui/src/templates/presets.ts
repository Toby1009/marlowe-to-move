export type PresetName =
  | 'escrow_usdc'
  | 'crowdfunding_usdc'
  | 'streaming_linear_usdc'
  | 'otc_swap_eth_usdc';

export const PRESET_SPECS: Record<PresetName, unknown> = {
  escrow_usdc: {
    when: [
      {
        case: {
          deposits: { constant: 1000 },
          party: { role_token: 'Buyer' },
          of_token: { currency_symbol: 'test::mock_usdc::USDC', token_name: 'USDC' },
          into_account: { role_token: 'Buyer' },
        },
        then: {
          when: [
            {
              case: {
                for_choice: {
                  choice_name: 'escrow_decision',
                  choice_owner: { role_token: 'Mediator' },
                },
                choose_between: [{ from: 0, to: 1 }],
              },
              then: {
                if: {
                  value: {
                    value_of_choice: {
                      choice_name: 'escrow_decision',
                      choice_owner: { role_token: 'Mediator' },
                    },
                  },
                  equal_to: { constant: 1 },
                },
                then: {
                  pay: { constant: 1000 },
                  from_account: { role_token: 'Buyer' },
                  to: { party: { role_token: 'Seller' } },
                  token: { currency_symbol: 'test::mock_usdc::USDC', token_name: 'USDC' },
                  then: 'close',
                },
                else: {
                  pay: { constant: 1000 },
                  from_account: { role_token: 'Buyer' },
                  to: { party: { role_token: 'Buyer' } },
                  token: { currency_symbol: 'test::mock_usdc::USDC', token_name: 'USDC' },
                  then: 'close',
                },
              },
            },
          ],
          timeout: 1800403200000,
          timeout_continuation: {
            pay: { constant: 1000 },
            from_account: { role_token: 'Buyer' },
            to: { party: { role_token: 'Buyer' } },
            token: { currency_symbol: 'test::mock_usdc::USDC', token_name: 'USDC' },
            then: 'close',
          },
        },
      },
    ],
    timeout: 1799971200000,
    timeout_continuation: 'close',
  },
  crowdfunding_usdc: {
    when: [
      {
        case: {
          deposits: { constant: 1000 },
          party: { role_token: 'Supporter' },
          of_token: { currency_symbol: 'test::mock_usdc::USDC', token_name: 'USDC' },
          into_account: { role_token: 'Project' },
        },
        then: {
          when: [
            {
              case: {
                notify_if: {
                  value: {
                    amount_of_token: { currency_symbol: 'test::mock_usdc::USDC', token_name: 'USDC' },
                    in_account: { role_token: 'Project' },
                  },
                  ge_than: { constant: 1000 },
                },
              },
              then: {
                pay: {
                  amount_of_token: { currency_symbol: 'test::mock_usdc::USDC', token_name: 'USDC' },
                  in_account: { role_token: 'Project' },
                },
                from_account: { role_token: 'Project' },
                to: { party: { role_token: 'Creator' } },
                token: { currency_symbol: 'test::mock_usdc::USDC', token_name: 'USDC' },
                then: 'close',
              },
            },
          ],
          timeout: 1801267200000,
          timeout_continuation: {
            pay: {
              amount_of_token: { currency_symbol: 'test::mock_usdc::USDC', token_name: 'USDC' },
              in_account: { role_token: 'Project' },
            },
            from_account: { role_token: 'Project' },
            to: { party: { role_token: 'Supporter' } },
            token: { currency_symbol: 'test::mock_usdc::USDC', token_name: 'USDC' },
            then: 'close',
          },
        },
      },
    ],
    timeout: 1800835200000,
    timeout_continuation: 'close',
  },
  streaming_linear_usdc: {
    when: [
      {
        case: {
          deposits: { constant: 3000 },
          party: { role_token: 'Payer' },
          of_token: { currency_symbol: 'test::mock_usdc::USDC', token_name: 'USDC' },
          into_account: { role_token: 'StreamVault' },
        },
        then: {
          when: [
            {
              case: {
                for_choice: {
                  choice_name: 'claim_1',
                  choice_owner: { role_token: 'Recipient' },
                },
                choose_between: [{ from: 1, to: 1 }],
              },
              then: {
                pay: { constant: 1000 },
                from_account: { role_token: 'StreamVault' },
                to: { party: { role_token: 'Recipient' } },
                token: { currency_symbol: 'test::mock_usdc::USDC', token_name: 'USDC' },
                then: {
                  when: [
                    {
                      case: {
                        for_choice: {
                          choice_name: 'claim_2',
                          choice_owner: { role_token: 'Recipient' },
                        },
                        choose_between: [{ from: 1, to: 1 }],
                      },
                      then: {
                        pay: { constant: 1000 },
                        from_account: { role_token: 'StreamVault' },
                        to: { party: { role_token: 'Recipient' } },
                        token: { currency_symbol: 'test::mock_usdc::USDC', token_name: 'USDC' },
                        then: {
                          when: [
                            {
                              case: {
                                for_choice: {
                                  choice_name: 'claim_3',
                                  choice_owner: { role_token: 'Recipient' },
                                },
                                choose_between: [{ from: 1, to: 1 }],
                              },
                              then: {
                                pay: {
                                  amount_of_token: { currency_symbol: 'test::mock_usdc::USDC', token_name: 'USDC' },
                                  in_account: { role_token: 'StreamVault' },
                                },
                                from_account: { role_token: 'StreamVault' },
                                to: { party: { role_token: 'Recipient' } },
                                token: { currency_symbol: 'test::mock_usdc::USDC', token_name: 'USDC' },
                                then: 'close',
                              },
                            },
                          ],
                          timeout: 1803859200000,
                          timeout_continuation: {
                            pay: {
                              amount_of_token: { currency_symbol: 'test::mock_usdc::USDC', token_name: 'USDC' },
                              in_account: { role_token: 'StreamVault' },
                            },
                            from_account: { role_token: 'StreamVault' },
                            to: { party: { role_token: 'Payer' } },
                            token: { currency_symbol: 'test::mock_usdc::USDC', token_name: 'USDC' },
                            then: 'close',
                          },
                        },
                      },
                    },
                  ],
                  timeout: 1803513600000,
                  timeout_continuation: {
                    pay: {
                      amount_of_token: { currency_symbol: 'test::mock_usdc::USDC', token_name: 'USDC' },
                      in_account: { role_token: 'StreamVault' },
                    },
                    from_account: { role_token: 'StreamVault' },
                    to: { party: { role_token: 'Payer' } },
                    token: { currency_symbol: 'test::mock_usdc::USDC', token_name: 'USDC' },
                    then: 'close',
                  },
                },
              },
            },
          ],
          timeout: 1803081600000,
          timeout_continuation: {
            pay: {
              amount_of_token: { currency_symbol: 'test::mock_usdc::USDC', token_name: 'USDC' },
              in_account: { role_token: 'StreamVault' },
            },
            from_account: { role_token: 'StreamVault' },
            to: { party: { role_token: 'Payer' } },
            token: { currency_symbol: 'test::mock_usdc::USDC', token_name: 'USDC' },
            then: 'close',
          },
        },
      },
    ],
    timeout: 1802649600000,
    timeout_continuation: 'close',
  },
  otc_swap_eth_usdc: {
    when: [
      {
        case: {
          deposits: { constant: 1000 },
          party: { role_token: 'PartyA' },
          of_token: { currency_symbol: 'test::mock_usdc::USDC', token_name: 'USDC' },
          into_account: { role_token: 'VaultA' },
        },
        then: {
          when: [
            {
              case: {
                deposits: { constant: 1 },
                party: { role_token: 'PartyB' },
                of_token: { currency_symbol: 'test::mock_eth::ETH', token_name: 'ETH' },
                into_account: { role_token: 'VaultB' },
              },
              then: {
                pay: { constant: 1000 },
                from_account: { role_token: 'VaultA' },
                to: { party: { role_token: 'PartyB' } },
                token: { currency_symbol: 'test::mock_usdc::USDC', token_name: 'USDC' },
                then: {
                  pay: { constant: 1 },
                  from_account: { role_token: 'VaultB' },
                  to: { party: { role_token: 'PartyA' } },
                  token: { currency_symbol: 'test::mock_eth::ETH', token_name: 'ETH' },
                  then: 'close',
                },
              },
            },
          ],
          timeout: 1804204800000,
          timeout_continuation: {
            pay: {
              amount_of_token: { currency_symbol: 'test::mock_usdc::USDC', token_name: 'USDC' },
              in_account: { role_token: 'VaultA' },
            },
            from_account: { role_token: 'VaultA' },
            to: { party: { role_token: 'PartyA' } },
            token: { currency_symbol: 'test::mock_usdc::USDC', token_name: 'USDC' },
            then: 'close',
          },
        },
      },
    ],
    timeout: 1803859200000,
    timeout_continuation: 'close',
  },
};
