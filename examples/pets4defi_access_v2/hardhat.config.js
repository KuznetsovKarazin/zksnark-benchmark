export default {
  networks: {
    l1: {type:'edr-simulated',chainType:'l1',hardfork:'osaka',chainId:31337,initialDate:'2026-10-20T12:00:00Z',throwOnTransactionFailures:false},
    op: {type:'edr-simulated',chainType:'op',hardfork:'isthmus',chainId:31338,initialDate:'2026-10-20T12:00:00Z',throwOnTransactionFailures:false},
  },
};
