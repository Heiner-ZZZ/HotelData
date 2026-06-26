/**
 * Map an amenity label to a Material Symbols icon name.
 * Covers 80+ common hotel amenities across all categories.
 * Each distinct amenity gets its own icon — no duplicates.
 */
export function amenityIcon(label: string): string {
  const l = label.toLowerCase();

  // ── Conectividad ──
  if (l.includes('wifi') || l.includes('internet') || l.includes('conexión')) return 'wifi';

  // ── Piscina / Agua ──
  if (l.includes('piscina') || l.includes('alberca') || l.includes('pool')) return 'pool';
  if (l.includes('jacuzzi') || l.includes('hidromasaje') || l.includes('bañera')) return 'hot_tub';
  if (l.includes('playa') || l.includes('beach') || l.includes('mar') || l.includes('oceano')) return 'beach_access';
  if (l.includes('marina') || l.includes('puerto') || l.includes('muelle')) return 'directions_boat';

  // ── Gastronomía ──
  if (l.includes('restaurant') || l.includes('comedor') || l.includes('buffet') || l.includes('comida') || l.includes('cena')) return 'restaurant';
  if (l.includes('desayuno') || l.includes('breakfast') || l.includes('buffet')) return 'free_breakfast';
  if (l.includes('bar') && !l.includes('snack') && !l.includes('caf') && !l.includes('mini')) return 'local_bar';
  if (l.includes('minibar') || l.includes('mini bar')) return 'local_bar';
  if (l.includes('cafetería') || l.includes('cafeter') || l.includes('cafe') || l.includes('coffee')) return 'coffee';
  if (l.includes('cocina') || l.includes('cocin') || l.includes('kitchenette') || l.includes('cocina equipada')) return 'cooking';
  if (l.includes('microondas') || l.includes('microwave')) return 'microwave';
  if (l.includes('horno') || l.includes('oven')) return 'oven_gen';
  if (l.includes('nevera') || l.includes('refrigerador') || l.includes('fridge') || l.includes('heladera') || l.includes('refrigerador')) return 'kitchen';
  if (l.includes('lavavajilla') || l.includes('dishwasher') || l.includes('lavaplatos') || l.includes('lava vajilla')) return 'dishwasher';
  if (l.includes('snack') || l.includes('botana') || l.includes('entremés') || l.includes('entremes')) return 'bakery_dining';
  if (l.includes('parrilla') || l.includes('asador') || l.includes('barbacoa') || l.includes('grill') || l.includes('bbq')) return 'outdoor_grill';

  // ── Bienestar / Spa ──
  if (l.includes('spa') || l.includes('masaje') || l.includes('sauna') || l.includes('termas')) return 'spa';
  if (l.includes('gimnasio') || l.includes('gym') || l.includes('fitness') || l.includes('ejercicio') || l.includes('deporte') || l.includes('yoga')) return 'fitness_center';
  if (l.includes('bienestar') || l.includes('wellness') || l.includes('relaj') || l.includes('meditación') || l.includes('meditacion')) return 'self_improvement';
  if (l.includes('vapor') || l.includes('steam') || l.includes('baño turco') || l.includes('hamam') || l.includes('turco')) return 'steam';

  // ── Estacionamiento / Transporte ──
  if (l.includes('estacionamiento') || l.includes('parqueo') || l.includes('parking') || l.includes('cochera') || l.includes('garaje')) return 'local_parking';
  if (l.includes('shuttle') || l.includes('transporte') || l.includes('aeropuerto') || l.includes('traslado') || l.includes('transfer')) return 'airport_shuttle';
  if (l.includes('carga') || l.includes('tesla') || l.includes('eléctrico') || l.includes('electric') || l.includes('ev ') || l.includes('vehículo eléctrico')) return 'ev_charger';
  if (l.includes('bicicle') || l.includes('bici') || l.includes('bike') || l.includes('ciclismo') || l.includes('bicycle')) return 'pedal_bike';

  // ── Climatización ──
  if (l.includes('aire') || l.includes('clima') || l.includes('calefac') || l.includes('acondicionado') || l.includes('hvac')) return 'ac_unit';
  if (l.includes('calefacción') || l.includes('calefaccion') || l.includes('caldera') || l.includes('radiador') || l.includes('calor')) return 'heat_pump';
  if (l.includes('ventilador') || l.includes('fan') || l.includes('ventilación') || l.includes('ventilacion')) return 'mode_fan';
  if (l.includes('chimenea') || l.includes('fireplace') || l.includes('hogar')) return 'fireplace';

  // ── Habitación ──
  if (l.includes('televisión') || l.includes('tv ') || l.includes('televisor') || l.includes('cable') || l.includes('television')) return 'tv';
  if (l.includes('teléfono') || l.includes('phone') || l.includes('telefono')) return 'phone';
  if (l.includes('caja') || l.includes('safe') || l.includes('seguro') || l.includes('valores') || l.includes('caja fuerte')) return 'lock';
  if (l.includes('plancha') || l.includes('iron') || l.includes('tabla') || l.includes('planchar')) return 'iron';
  if (l.includes('secador') || l.includes('hair dryer') || l.includes('pelo') || l.includes('secador de pelo')) return 'dry';
  if (l.includes('cuna') || l.includes('camas extra') || l.includes('cama extra') || l.includes('cuna')) return 'crib';
  if (l.includes('balcón') || l.includes('balcon') || l.includes('terraza') || l.includes('patio')) return 'balcony';
  if (l.includes('vista') || l.includes('view') || l.includes('panorá') || l.includes('panorama') || l.includes('mirador')) return 'panorama';
  if (l.includes('insonor') || l.includes('soundproof') || l.includes('sonido') || l.includes('ruido') || l.includes('silenci')) return 'sound_detection_dog_barking';
  if (l.includes('escritorio') || l.includes('desk') || l.includes('mesa trabajo') || l.includes('work desk')) return 'desk';
  if (l.includes('ropero') || l.includes('armario') || l.includes('closet') || l.includes('wardrobe') || l.includes('guardarropa')) return 'shelves';
  if (l.includes('espejo') || l.includes('mirror') || l.includes('tocador')) return 'mirror';
  if (l.includes('alfombra') || l.includes('carpet') || l.includes('tapete')) return 'carpet';

  // ── Mascotas ──
  if (l.includes('mascota') || l.includes('perro') || l.includes('pet ') || l.includes('animal') || l.includes('mascotas') || l.includes('dog')) return 'pets';

  // ── Lavandería / Limpieza ──
  if (l.includes('lavandería') || l.includes('laundry') || l.includes('lavado') || l.includes('tintorería') || l.includes('lavanderia') || l.includes('lavander')) return 'local_laundry_service';
  if (l.includes('limpieza') || l.includes('housekeeping') || l.includes('clean') || l.includes('aseo') || l.includes('aseo')) return 'cleaning_services';
  if (l.includes('aspiradora') || l.includes('vacuum') || l.includes('aspirador')) return 'vacuum';

  // ── Servicios ──
  if (l.includes('recepc') || l.includes('conserje') || l.includes('concierge') || l.includes('24 hora') || l.includes('24h') || l.includes('recepcion')) return 'concierge';
  if (l.includes('servicio') || l.includes('room service') || l.includes('roomservice') || l.includes('a la habitación') || l.includes('a la habitacion')) return 'room_service';
  if (l.includes('equipaje') || l.includes('luggage') || l.includes('maleta') || l.includes('guard') || l.includes('equipajes') || l.includes('maletas')) return 'luggage';
  if (l.includes('ascensor') || l.includes('elevador') || l.includes('elevator') || l.includes('ascensor')) return 'elevator';
  if (l.includes('accesibil') || l.includes('silla') || l.includes('rampa') || l.includes('discapac') || l.includes('accesible') || l.includes('wheelchair')) return 'accessible';

  // ── Negocios ──
  if (l.includes('negocio') || l.includes('reunión') || l.includes('business') || l.includes('ejecutiva') || l.includes('reunion') || l.includes('meeting')) return 'business_center';
  if (l.includes('salón') || l.includes('salon') || l.includes('evento') || l.includes('fiesta') || l.includes('celebracion') || l.includes('banquete')) return 'celebration';
  if (l.includes('impresora') || l.includes('printer') || l.includes('fax') || l.includes('copiad')) return 'print';
  if (l.includes('proyector') || l.includes('projector') || l.includes('pantalla') || l.includes('multimedia')) return 'projector';

  // ── Exteriores / Naturaleza ──
  if (l.includes('jardín') || l.includes('garden') || l.includes('jardin') || l.includes('parque')) return 'yard';
  if (l.includes('montaña') || l.includes('montana') || l.includes('monta') || l.includes('mountain') || l.includes('senderismo')) return 'landscape';
  if (l.includes('no fum') || l.includes('smoke') || l.includes('fumar') || l.includes('humo') || l.includes('no fumar')) return 'smoke_free';
  if (l.includes('popular') || l.includes('destacado') || l.includes('favorito') || l.includes('común') || l.includes('top') || l.includes('recomendado')) return 'star';
  if (l.includes('golf') || l.includes('tenis') || l.includes('cancha') || l.includes('deporte')) return 'sports_tennis';
  if (l.includes('yoga') || l.includes('meditación') || l.includes('pilates')) return 'fitness_center';

  // ── Habitaciones / Familia ──
  if (l.includes('habita') || l.includes('familia') || l.includes('familiar') || l.includes('dormitorio') || l.includes('cuarto')) return 'meeting_room';
  if (l.includes('conectad') || l.includes('comunica') || l.includes('adyacente') || l.includes('contigua') || l.includes('connecting')) return 'door_sliding';

  // ── Tecnología ──
  if (l.includes('altavoz') || l.includes('speaker') || l.includes('parlante') || l.includes('bocina') || l.includes('bluetooth')) return 'speaker';
  if (l.includes('streaming') || l.includes('netflix') || l.includes('chromecast') || l.includes('app') || l.includes('smart tv')) return 'smart_display';
  if (l.includes('cargador') || l.includes('charger') || l.includes('usb') || l.includes('toma') || l.includes('enchufe')) return 'cable';
  if (l.includes('seguridad') || l.includes('camara') || l.includes('cámara') || l.includes('camera') || l.includes('alarma')) return 'security';

  // ── Default ──
  return 'check_box';
}
