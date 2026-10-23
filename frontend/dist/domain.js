export const limits={min:100000,max:10000000,minMonths:6,maxMonths:60};
export function calculate(amount,months,purpose='Оборотные средства'){
 if(!Number.isFinite(amount)||amount<limits.min||amount>limits.max||!Number.isInteger(months)||months<6||months>60)throw new Error('Проверьте сумму и срок');
 const rate=purpose==='Оборудование'?19.5:21.5;const r=rate/1200;const payment=amount*r/(1-Math.pow(1+r,-months));return {rate,payment,total:payment*months,interest:payment*months-amount};
}
