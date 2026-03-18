import React, { useEffect, useRef, useCallback } from 'react';
import { setOptions, importLibrary } from '@googlemaps/js-api-loader';
import { Map as MapIcon } from 'lucide-react';
import { OptimizedChain, ChainLeg } from '../types';
import { API_BASE_URL } from '../services/api';

// Internal tool — key from backend config.py
const GOOGLE_MAPS_API_KEY = 'AIzaSyALo74rhV07y9M4kQF_yxP7gt0b4tJjn3A';

let optionsSet = false;

interface RouteMapViewProps {
  chain: OptimizedChain;
  startCity: string;
  homeBase: string;
}

const darkMapStyle: google.maps.MapTypeStyle[] = [
  { elementType: 'geometry', stylers: [{ color: '#1e293b' }] },
  { elementType: 'labels.text.stroke', stylers: [{ color: '#0f172a' }] },
  { elementType: 'labels.text.fill', stylers: [{ color: '#94a3b8' }] },
  { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#334155' }] },
  { featureType: 'road', elementType: 'labels.text.fill', stylers: [{ color: '#64748b' }] },
  { featureType: 'road.highway', elementType: 'geometry', stylers: [{ color: '#475569' }] },
  { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#0c4a6e' }] },
  { featureType: 'poi', stylers: [{ visibility: 'off' }] },
  { featureType: 'transit', stylers: [{ visibility: 'off' }] },
];

interface TrihaulSuggestion {
  city: string;
  state: string;
  tier: number;
  extraMiles: number;
  reason: string;
  lat?: number;
  lng?: number;
}

interface StopPosition {
  position: google.maps.LatLng;
  label: string;
  leg: ChainLeg;
  index: number;
}

export default function RouteMapView({ chain, startCity, homeBase }: RouteMapViewProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<google.maps.Map | null>(null);
  const markersRef = useRef<google.maps.Marker[]>([]);
  const renderersRef = useRef<google.maps.DirectionsRenderer[]>([]);
  const infoWindowRef = useRef<google.maps.InfoWindow | null>(null);
  const polylinesRef = useRef<google.maps.Polyline[]>([]);

  const cleanup = useCallback(() => {
    markersRef.current.forEach(m => m.setMap(null));
    markersRef.current = [];
    renderersRef.current.forEach(r => r.setMap(null));
    renderersRef.current = [];
    polylinesRef.current.forEach(p => p.setMap(null));
    polylinesRef.current = [];
    if (infoWindowRef.current) {
      infoWindowRef.current.close();
    }
  }, []);

  useEffect(() => {
    if (!mapRef.current || chain.legs.length === 0) return;

    if (!optionsSet) {
      setOptions({ key: GOOGLE_MAPS_API_KEY, v: 'weekly' });
      optionsSet = true;
    }

    let cancelled = false;

    // Load the core maps library first, then others in parallel
    importLibrary('maps').then(async () => {
      if (cancelled || !mapRef.current) return;

      // Load additional libraries
      await Promise.all([
        importLibrary('routes'),
        importLibrary('geometry'),
      ]);

      if (cancelled || !mapRef.current) return;

      cleanup();

      const map = new google.maps.Map(mapRef.current, {
        center: { lat: 39.8283, lng: -98.5795 },
        zoom: 5,
        styles: darkMapStyle,
        disableDefaultUI: true,
        zoomControl: true,
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: true,
      });
      mapInstanceRef.current = map;
      infoWindowRef.current = new google.maps.InfoWindow();

      renderRoutes(map);
    }).catch(err => {
      console.error('Failed to load Google Maps:', err);
    });

    return () => {
      cancelled = true;
      cleanup();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chain]);

  const renderRoutes = async (map: google.maps.Map) => {
    const directionsService = new google.maps.DirectionsService();
    const bounds = new google.maps.LatLngBounds();
    const stopPositions: StopPosition[] = [];

    const legs = chain.legs;

    for (let i = 0; i < legs.length; i++) {
      const leg = legs[i];
      const origin = leg.load?.origin || leg.result?.origin || '';
      const destination = leg.load?.destination || leg.result?.destination || '';

      if (!origin || !destination) continue;

      try {
        const result = await new Promise<google.maps.DirectionsResult>((resolve, reject) => {
          directionsService.route(
            {
              origin,
              destination,
              travelMode: google.maps.TravelMode.DRIVING,
            },
            (response, status) => {
              if (status === 'OK' && response) {
                resolve(response);
              } else {
                reject(new Error(`Directions failed: ${status}`));
              }
            }
          );
        });

        if (!result.routes[0]) {
          drawFallbackLine(map, origin, destination, leg, bounds);
          continue;
        }

        // Determine line style
        const isReturnHome = leg.isReturnHome || false;
        const isDeadhead = !isReturnHome && leg.deadhead > 0 && !leg.load;

        let polylineOptions: google.maps.PolylineOptions;

        if (isReturnHome) {
          polylineOptions = {
            strokeColor: '#3b82f6',
            strokeOpacity: 0,
            strokeWeight: 3,
            icons: [{
              icon: { path: 'M 0,-1 0,1', strokeOpacity: 0.8, strokeWeight: 3, scale: 3 },
              offset: '0',
              repeat: '15px',
            }],
          };
        } else if (isDeadhead) {
          polylineOptions = {
            strokeColor: '#f59e0b',
            strokeOpacity: 0,
            strokeWeight: 3,
            icons: [{
              icon: { path: 'M 0,-1 0,1', strokeOpacity: 0.8, strokeWeight: 3, scale: 3 },
              offset: '0',
              repeat: '15px',
            }],
          };
        } else {
          polylineOptions = {
            strokeColor: '#22c55e',
            strokeOpacity: 0.85,
            strokeWeight: 4,
          };
        }

        const renderer = new google.maps.DirectionsRenderer({
          map,
          directions: result,
          suppressMarkers: true,
          preserveViewport: true,
          polylineOptions,
        });
        renderersRef.current.push(renderer);

        // Extract start/end positions for markers
        const routeLeg = result.routes[0].legs[0];
        if (routeLeg) {
          bounds.extend(routeLeg.start_location);
          bounds.extend(routeLeg.end_location);

          if (i === 0) {
            stopPositions.push({
              position: routeLeg.start_location,
              label: 'H',
              leg,
              index: -1,
            });
          }

          if (!isReturnHome) {
            stopPositions.push({
              position: routeLeg.end_location,
              label: String(stopPositions.filter(s => s.index >= 0).length + 1),
              leg,
              index: i,
            });
          }
        }
      } catch (err) {
        console.warn(`Directions API failed for leg ${i}:`, err);
        drawFallbackLine(map, origin, destination, leg, bounds);
      }
    }

    addMarkers(map, stopPositions);

    if (!bounds.isEmpty()) {
      map.fitBounds(bounds, { top: 60, right: 60, bottom: 60, left: 60 });
    }

    fetchTrihaulSuggestions(map, bounds);
  };

  const drawFallbackLine = (
    map: google.maps.Map,
    origin: string,
    destination: string,
    leg: ChainLeg,
    bounds: google.maps.LatLngBounds
  ) => {
    const geocoder = new google.maps.Geocoder();

    const geocodePromise = (address: string): Promise<google.maps.LatLng | null> =>
      new Promise(resolve => {
        geocoder.geocode({ address }, (results, status) => {
          if (status === 'OK' && results && results[0]) {
            resolve(results[0].geometry.location);
          } else {
            resolve(null);
          }
        });
      });

    Promise.all([geocodePromise(origin), geocodePromise(destination)]).then(([start, end]) => {
      if (!start || !end) return;

      bounds.extend(start);
      bounds.extend(end);

      const isReturnHome = leg.isReturnHome || false;
      const color = isReturnHome ? '#3b82f6' : '#22c55e';

      const polyline = new google.maps.Polyline({
        path: [start, end],
        strokeColor: color,
        strokeOpacity: isReturnHome ? 0.5 : 0.8,
        strokeWeight: 3,
        map,
      });
      polylinesRef.current.push(polyline);

      if (mapInstanceRef.current && !bounds.isEmpty()) {
        mapInstanceRef.current.fitBounds(bounds, { top: 60, right: 60, bottom: 60, left: 60 });
      }
    });
  };

  const addMarkers = (map: google.maps.Map, stops: StopPosition[]) => {
    const infoWindow = infoWindowRef.current!;

    stops.forEach(stop => {
      const isHome = stop.index === -1;

      const marker = new google.maps.Marker({
        position: stop.position,
        map,
        label: {
          text: isHome ? '\u2302' : stop.label,
          color: '#ffffff',
          fontWeight: 'bold',
          fontSize: isHome ? '16px' : '12px',
        },
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: isHome ? 16 : 14,
          fillColor: isHome ? '#f59e0b' : '#22c55e',
          fillOpacity: 1,
          strokeColor: '#0f172a',
          strokeWeight: 3,
        },
        zIndex: isHome ? 100 : 50 + stop.index,
      });

      marker.addListener('click', () => {
        const leg = stop.leg;
        const load = leg.load;
        const result = leg.result;
        const originLabel = load?.origin || result?.origin || '';
        const destLabel = load?.destination || result?.destination || '';
        const rate = load?.rate || result?.rate || 0;
        const profit = result?.profit ?? 0;
        const miles = load?.miles || result?.miles || 0;
        const driveHours = result?.driveHours || 0;
        const score = result?.score ?? 0;
        const action = result?.action || '';

        const profitColor = profit >= 0 ? '#22c55e' : '#ef4444';
        const actionColor =
          action === 'BOOK IT' ? '#22c55e'
          : action === 'CONSIDER' ? '#eab308'
          : action === 'NEGOTIATE' ? '#f97316'
          : '#ef4444';

        if (isHome) {
          infoWindow.setContent(`
            <div style="background:#1e293b;color:#e2e8f0;padding:12px 16px;border-radius:8px;min-width:150px;font-family:system-ui,sans-serif;">
              <div style="font-size:14px;font-weight:800;color:#f59e0b;margin-bottom:4px;">HOME BASE</div>
              <div style="font-size:13px;color:#cbd5e1;">${homeBase}</div>
            </div>
          `);
        } else if (leg.isReturnHome) {
          infoWindow.setContent(`
            <div style="background:#1e293b;color:#e2e8f0;padding:12px 16px;border-radius:8px;min-width:180px;font-family:system-ui,sans-serif;">
              <div style="font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:6px;">Return Home</div>
              <div style="font-size:13px;color:#cbd5e1;margin-bottom:4px;">${originLabel} &rarr; ${destLabel}</div>
              <div style="font-size:12px;color:#94a3b8;">${miles} mi &bull; ${driveHours.toFixed(1)} hrs</div>
            </div>
          `);
        } else {
          infoWindow.setContent(`
            <div style="background:#1e293b;color:#e2e8f0;padding:12px 16px;border-radius:8px;min-width:220px;font-family:system-ui,sans-serif;">
              <div style="font-size:13px;font-weight:700;color:#cbd5e1;margin-bottom:8px;">${originLabel} &rarr; ${destLabel}</div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px 16px;font-size:12px;">
                <div><span style="color:#64748b;">Rate:</span> <span style="color:#fff;font-weight:700;">$${rate.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span></div>
                <div><span style="color:#64748b;">Profit:</span> <span style="color:${profitColor};font-weight:700;">$${Math.abs(profit).toLocaleString(undefined, { minimumFractionDigits: 2 })}</span></div>
                <div><span style="color:#64748b;">Miles:</span> <span style="color:#fff;">${miles} mi</span></div>
                <div><span style="color:#64748b;">Drive:</span> <span style="color:#fff;">${driveHours.toFixed(1)} hrs</span></div>
              </div>
              ${action ? `
              <div style="margin-top:8px;display:flex;align-items:center;gap:8px;">
                <span style="font-size:12px;color:#64748b;">Score: <strong style="color:#fff;">${score > 0 ? '+' + score : score}</strong></span>
                <span style="background:${actionColor};color:#000;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:800;text-transform:uppercase;">${action}</span>
              </div>` : ''}
            </div>
          `);
        }
        infoWindow.open(map, marker);
      });

      markersRef.current.push(marker);
    });
  };

  const fetchTrihaulSuggestions = async (map: google.maps.Map, bounds: google.maps.LatLngBounds) => {
    const nonReturnLegs = chain.legs.filter(l => !l.isReturnHome);
    if (nonReturnLegs.length === 0) return;

    const lastLeg = nonReturnLegs[nonReturnLegs.length - 1];
    const lastDest = lastLeg.load?.destination || lastLeg.result?.destination || '';
    if (!lastDest) return;

    const parts = lastDest.split(', ');
    if (parts.length < 2) return;

    const currentCity = parts[0].trim();
    const currentState = parts[1].trim();

    try {
      const res = await fetch(`${API_BASE_URL}/api/trihaul/suggestions?current_city=${encodeURIComponent(currentCity)}&current_state=${encodeURIComponent(currentState)}`);
      if (!res.ok) return;
      const suggestions: TrihaulSuggestion[] = await res.json();
      if (!suggestions || suggestions.length === 0) return;

      const geocoder = new google.maps.Geocoder();
      const infoWindow = infoWindowRef.current!;

      for (const suggestion of suggestions.slice(0, 5)) {
        const address = `${suggestion.city}, ${suggestion.state}`;

        geocoder.geocode({ address }, (results, status) => {
          if (status !== 'OK' || !results || !results[0]) return;

          const position = results[0].geometry.location;
          bounds.extend(position);

          const tierColors: Record<number, string> = { 1: '#22c55e', 2: '#eab308', 3: '#f97316' };
          const tierLabels: Record<number, string> = { 1: 'HOT', 2: 'WARM', 3: 'MODERATE' };

          const marker = new google.maps.Marker({
            position,
            map,
            opacity: 0.7,
            icon: {
              path: 'M-4,-8 0,-14 4,-8 4,0 -4,0Z',
              scale: 1.4,
              fillColor: '#a855f7',
              fillOpacity: 0.8,
              strokeColor: '#7c3aed',
              strokeWeight: 2,
            },
            zIndex: 30,
          });

          marker.addListener('click', () => {
            const tierColor = tierColors[suggestion.tier] || '#94a3b8';
            const tierLabel = tierLabels[suggestion.tier] || `Tier ${suggestion.tier}`;

            infoWindow.setContent(`
              <div style="background:#1e293b;color:#e2e8f0;padding:12px 16px;border-radius:8px;min-width:200px;font-family:system-ui,sans-serif;">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
                  <span style="font-size:14px;font-weight:800;color:#a855f7;">${suggestion.city}, ${suggestion.state}</span>
                  <span style="background:${tierColor};color:#000;padding:1px 6px;border-radius:4px;font-size:9px;font-weight:800;">${tierLabel}</span>
                </div>
                <div style="font-size:12px;color:#94a3b8;margin-bottom:4px;">+${suggestion.extraMiles || '?'} mi from last stop</div>
                <div style="font-size:11px;color:#cbd5e1;line-height:1.4;">${suggestion.reason || 'Trihaul opportunity'}</div>
              </div>
            `);
            infoWindow.open(map, marker);
          });

          markersRef.current.push(marker);
        });
      }
    } catch {
      // Trihaul API not available — silently ignore
    }
  };

  return (
    <div className="mb-12">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-8 h-8 bg-slate-800 rounded-lg flex items-center justify-center">
          <MapIcon size={16} className="text-amber-500" />
        </div>
        <h2 className="text-lg font-black text-white uppercase tracking-wider">Route Map</h2>
      </div>

      {/* Map Container */}
      <div className="relative rounded-2xl border border-slate-800 overflow-hidden bg-slate-900">
        <div ref={mapRef} style={{ width: '100%', height: 500 }} />

        {/* Legend */}
        <div className="absolute bottom-4 left-4 bg-slate-900/90 backdrop-blur border border-slate-700 rounded-xl px-4 py-3 space-y-2">
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Legend</div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-0.5 bg-green-500 rounded" />
            <span className="text-xs text-slate-300">Loaded</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 border-t-2 border-dashed border-amber-500" />
            <span className="text-xs text-slate-300">Deadhead</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 border-t-2 border-dashed border-blue-500" />
            <span className="text-xs text-slate-300">Return Home</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-purple-500/80 rotate-45 rounded-sm" />
            <span className="text-xs text-slate-300">Trihaul Opportunity</span>
          </div>
        </div>
      </div>
    </div>
  );
}
