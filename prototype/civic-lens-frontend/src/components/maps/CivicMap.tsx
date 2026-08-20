import React from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMapEvents, Circle, useMap } from 'react-leaflet';
import L from 'leaflet';

// Fix Leaflet default icon paths in bundlers
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
});

interface Pin {
  id: string;
  lat: number;
  lng: number;
  title: string;
  category?: string;
  status?: string;
  fuzzed?: boolean;
  priority?: string;
  department?: string;
}

export interface HotspotCircle {
  id: string;
  lat: number;
  lng: number;
  radius: number;
  score: number;
  count: number;
}

interface CivicMapProps {
  center?: [number, number];
  zoom?: number;
  pins?: Pin[];
  hotspots?: HotspotCircle[];
  selectedLocation?: [number, number] | null;
  onLocationSelect?: (lat: number, lng: number) => void;
  selectedPinId?: string | null;
  onPinSelect?: (id: string) => void;
  interactivePinPicker?: boolean;
  className?: string;
}

function LocationPickerEvents({ onSelect }: { onSelect?: (lat: number, lng: number) => void }) {
  useMapEvents({
    click(e) {
      if (onSelect) {
        onSelect(e.latlng.lat, e.latlng.lng);
      }
    },
  });

  return null;
}

function MapUpdater({ selectedLocation, selectedPinId, pins }: { selectedLocation?: [number, number] | null, selectedPinId?: string | null, pins?: Pin[] }) {
  const map = useMap();
  React.useEffect(() => {
    if (selectedLocation) {
      map.flyTo(selectedLocation, 15, { animate: true, duration: 1.5 });
    } else if (selectedPinId && pins) {
      const pin = pins.find(p => p.id === selectedPinId);
      if (pin) {
        map.flyTo([pin.lat, pin.lng], 16, { animate: true, duration: 1.5 });
      }
    }
  }, [selectedLocation, selectedPinId, pins, map]);
  return null;
}

const getMarkerIcon = (priority?: string, isSelected?: boolean) => {
  const colorClass = 
    priority === 'CRITICAL' ? 'bg-red-500 border-red-200' :
    priority === 'HIGH' ? 'bg-orange-500 border-orange-200' :
    priority === 'MEDIUM' ? 'bg-amber-400 border-amber-100' :
    'bg-emerald-500 border-emerald-200';

  const pulseClass = (priority === 'CRITICAL' || priority === 'HIGH') ? 'animate-pulse' : '';
  const scaleClass = isSelected ? 'scale-150 z-50' : 'scale-100';

  return L.divIcon({
    className: 'custom-leaflet-marker',
    html: `<div class="relative w-6 h-6 rounded-full border-2 shadow-lg transition-transform duration-300 ${colorClass} ${scaleClass} flex items-center justify-center">
             ${(priority === 'CRITICAL' || priority === 'HIGH') ? `<div class="absolute inset-0 rounded-full border-2 border-white opacity-50 ${pulseClass}"></div>` : ''}
           </div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -12]
  });
};

export const CivicMap: React.FC<CivicMapProps> = ({
  center = [20.2961, 85.8245], // Default Bhubaneswar map center bounds
  zoom = 13,
  pins = [],
  hotspots = [],
  selectedLocation,
  onLocationSelect,
  selectedPinId,
  onPinSelect,
  interactivePinPicker = false,
  className = 'h-80 w-full rounded-xl overflow-hidden shadow-lg border border-slate-200',
}) => {
  const mapCenter = selectedLocation || center;

  return (
    <div className={className}>
      <MapContainer center={mapCenter} zoom={zoom} zoomControl={false} scrollWheelZoom={true} className="h-full w-full">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Selected location marker if provided */}
        {selectedLocation && (
          <Marker
            position={selectedLocation}
            draggable={interactivePinPicker}
            eventHandlers={{
              dragend: (e) => {
                const marker = e.target;
                const position = marker.getLatLng();
                onLocationSelect?.(position.lat, position.lng);
              },
            }}
          >
            <Popup>Picked Location: {selectedLocation[0].toFixed(4)}, {selectedLocation[1].toFixed(4)}</Popup>
          </Marker>
        )}

        {/* Interactive picker listener */}
        {interactivePinPicker && <LocationPickerEvents onSelect={onLocationSelect} />}

        <MapUpdater selectedLocation={selectedLocation} selectedPinId={selectedPinId} pins={pins} />

        {/* Public & Operator Issue Pins */}
        {pins.map((pin) => (
          <Marker 
            key={pin.id} 
            position={[pin.lat, pin.lng]}
            icon={getMarkerIcon(pin.priority, pin.id === selectedPinId)}
            eventHandlers={{
              click: () => onPinSelect?.(pin.id)
            }}
          >
            <Popup>
              <div className="p-2 min-w-[200px]">
                <div className="flex justify-between items-start mb-2">
                  <span className="font-bold text-sm block leading-tight pr-4 text-slate-800">{pin.title}</span>
                </div>
                {pin.category && <span className="text-xs text-blue-600 font-bold block">{pin.category}</span>}
                {pin.department && <span className="text-[10px] text-slate-500 block uppercase tracking-wide mt-1">{pin.department}</span>}
                {pin.priority && (
                  <span className={`inline-block text-[10px] px-2 py-0.5 rounded font-bold mt-2 ${
                    pin.priority === 'CRITICAL' ? 'bg-red-100 text-red-700' :
                    pin.priority === 'HIGH' ? 'bg-orange-100 text-orange-700' :
                    pin.priority === 'MEDIUM' ? 'bg-amber-100 text-amber-700' :
                    'bg-emerald-100 text-emerald-700'
                  }`}>
                    {pin.priority} PRIORITY
                  </span>
                )}
                {pin.status && (
                  <span className="text-xs text-emerald-600 block font-semibold mt-2 border-t pt-2">Status: {pin.status}</span>
                )}
                
                {onPinSelect && (
                  <a href={`/operator/issues/${pin.id}`} className="mt-3 block w-full text-center bg-blue-600 text-slate-900 text-xs py-1.5 rounded-lg hover:bg-blue-700 transition-colors">
                    View Issue Details
                  </a>
                )}
              </div>
            </Popup>
          </Marker>
        ))}

        {/* Hotspot Circles */}
        {hotspots.map((hs) => (
          <Circle
            key={hs.id}
            center={[hs.lat, hs.lng]}
            radius={hs.radius || 300}
            pathOptions={{
              color: hs.score > 70 ? '#ef4444' : hs.score > 40 ? '#f59e0b' : '#3b82f6',
              fillColor: hs.score > 70 ? '#ef4444' : hs.score > 40 ? '#f59e0b' : '#3b82f6',
              fillOpacity: 0.3,
            }}
          >
            <Popup>
              <div className="p-1">
                <span className="font-bold text-sm block">Civic Hotspot Cluster</span>
                <span className="text-xs text-slate-700 block mt-1">Complaints: {hs.count}</span>
                <span className="text-xs text-amber-400 font-semibold block">Hotspot Score: {hs.score}</span>
              </div>
            </Popup>
          </Circle>
        ))}
      </MapContainer>
    </div>
  );
};
