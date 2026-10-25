export function payment(amount,months,rate){const r=rate/1200;return r?amount*r/(1-(1+r)**-months):amount/months}
