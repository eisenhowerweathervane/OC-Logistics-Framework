import { Load } from '../types';
import { CITIES, COMMODITIES } from '../constants';

export function generateRandomLoads(count: number): Load[] {
  const loads: Load[] = [];
  for (let i = 0; i < count; i++) {
    const origin = CITIES[Math.floor(Math.random() * CITIES.length)].name;
    let destination = CITIES[Math.floor(Math.random() * CITIES.length)].name;
    while (destination === origin) {
      destination = CITIES[Math.floor(Math.random() * CITIES.length)].name;
    }

    // Realistic miles (roughly based on corridor)
    const miles = Math.floor(Math.random() * 350) + 50;
    
    // Rates: $1.50 - $4.50 per mile
    const rpm = Math.random() * 3 + 1.5;
    const rate = Math.round(miles * rpm);

    const weight = Math.floor(Math.random() * 19000) + 25000;
    const commodity = COMMODITIES[Math.floor(Math.random() * COMMODITIES.length)];
    
    // Detention: mostly 0, some 1-2, rare 3+
    const detRand = Math.random();
    let detentionHours = 0;
    if (detRand > 0.7) detentionHours = Math.floor(Math.random() * 2) + 1;
    if (detRand > 0.95) detentionHours = Math.floor(Math.random() * 3) + 3;

    // Times: Pickup today between 6am and 2pm
    const now = new Date();
    const pickupDate = new Date(now);
    pickupDate.setHours(6 + Math.floor(Math.random() * 8), 0, 0, 0);
    
    // Delivery: miles / 50 + load/unload time + buffer
    const travelTimeHours = (miles / 50) + 2; 
    const deliveryDate = new Date(pickupDate);
    deliveryDate.setHours(deliveryDate.getHours() + travelTimeHours + Math.floor(Math.random() * 4) + 2);

    loads.push({
      id: `L-${Math.random().toString(36).substr(2, 6).toUpperCase()}`,
      origin,
      destination,
      miles,
      rate,
      weight,
      commodity,
      detentionHours,
      pickupWindowStart: pickupDate.toISOString(),
      deliveryDeadline: deliveryDate.toISOString()
    });
  }
  return loads;
}
