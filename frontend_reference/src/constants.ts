import { City, Assumptions } from './types';

export const CITIES: City[] = [
  { name: "Cleveland, OH", lat: 41.4993, lng: -81.6944 },
  { name: "Pittsburgh, PA", lat: 40.4406, lng: -79.9959 },
  { name: "Columbus, OH", lat: 39.9612, lng: -82.9988 },
  { name: "Cincinnati, OH", lat: 39.1031, lng: -84.5120 },
  { name: "Indianapolis, IN", lat: 39.7684, lng: -86.1581 },
  { name: "Buffalo, NY", lat: 42.8864, lng: -78.8784 },
  { name: "Detroit, MI", lat: 42.3314, lng: -83.0458 },
  { name: "Louisville, KY", lat: 38.2527, lng: -85.7585 },
  { name: "Chicago, IL", lat: 41.8781, lng: -87.6298 },
  { name: "Toledo, OH", lat: 41.6528, lng: -83.5379 },
  { name: "Akron, OH", lat: 41.0814, lng: -81.5190 },
  { name: "Dayton, OH", lat: 39.7589, lng: -84.1916 },
  { name: "Erie, PA", lat: 42.1292, lng: -80.0851 },
  { name: "Fort Wayne, IN", lat: 41.0793, lng: -85.1394 },
  { name: "Lexington, KY", lat: 38.0406, lng: -84.5037 },
  { name: "Nashville, TN", lat: 36.1627, lng: -86.7816 },
  { name: "St. Louis, MO", lat: 38.6270, lng: -90.1994 },
  { name: "Philadelphia, PA", lat: 39.9526, lng: -75.1652 },
  { name: "Charlotte, NC", lat: 35.2271, lng: -80.8431 },
  { name: "Atlanta, GA", lat: 33.7490, lng: -84.3880 },
  { name: "Memphis, TN", lat: 35.1495, lng: -90.0490 },
];

export const DEFAULT_ASSUMPTIONS: Assumptions = {
  fuelPrice: 3.85,
  mpg: 6.5,
  driverPay: 0.55,
  truckLease: 0.22,
  insurance: 0.08,
  maintReserve: 0.00,
  overhead: 0.04,
  factoringFee: 3.0,
  detentionRate: 50,
  maxDeadhead: 15,
  minMargin: 15,
  targetMargin: 25,
  avgSpeed: 52,
  loadUnloadTime: 1.5,
  daysAway: 0,
  homeBase: "Cleveland, OH",
};

export const COMMODITIES = [
  "Steel", "Auto Parts", "Building Materials", "Consumer Goods", 
  "Food Grade", "Paper Products", "Electronics", "Machinery", 
  "Plastics", "Medical Supplies", "Chemical (non-hazmat)"
];
