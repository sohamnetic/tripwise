// Look & feel per destination: its animated scene, emoji, tagline and explore categories.
import type { Far, Ground, Landmark, Motion, SceneSpec, Sky } from "../scenes/types";

export type SceneKind = "beach" | "hills" | "heritage" | "river" | "city";
export type Tag = "beaches" | "mountains" | "heritage" | "spiritual" | "wildlife" | "backwaters" | "cities" | "abroad";

export interface Vibe {
  spec: SceneSpec;
  scene: SceneKind; // broad kind, used for packing lists
  emoji: string;
  tagline: string;
  tags: Tag[];
  accent: string; // highlight colour on the trip page
  tint: string; // soft background wash
}

type Look = [SceneSpec, string, string, Tag[]];

const S = (sky: Sky, far: Far, ground: Ground, landmark: Landmark | null, motions: Motion[], extra: Partial<SceneSpec> = {}): SceneSpec => ({
  sky, far, ground, motions, ...(landmark ? { landmark } : {}), ...extra,
});

export const LOOKS: Record<string, Look> = {
  // big cities
  kolkata: [S("dusk", "skyline", "river", "howrah", ["rowboats", "birds"], { ls: 0.85 }), "🚋", "Trams, adda & mishti", ["cities", "heritage"]],
  delhi: [S("day", "skyline", "city", "indiaGate", ["rickshaw", "kites", "birds"]), "🕌", "History on every corner", ["cities", "heritage"]],
  mumbai: [S("sunset", "skyline", "sea", "gateway", ["sailboat", "birds"]), "🌃", "Sea face, vada pav & big dreams", ["cities", "beaches"]],
  bengaluru: [S("day", "skyline", "city", "palace", ["rickshaw", "birds"], { ls: 0.8 }), "☕", "Gardens, cafés & breweries", ["cities"]],
  chennai: [S("day", "skyline", "sea", "lighthouse", ["rowboats", "kites"]), "☕", "Marina, filter coffee & temples", ["cities", "beaches"]],
  hyderabad: [S("sunset", "skyline", "city", "charminar", ["rickshaw", "birds"]), "🍛", "Biryani & the Charminar", ["cities", "heritage"]],
  pune: [S("day", "hills", "city", "ruinFort", ["rickshaw", "birds"], { ls: 0.7 }), "🏙️", "Forts, food & weekend getaways", ["cities"]],
  ahmedabad: [S("day", "skyline", "city", null, ["kites", "rickshaw"]), "🪁", "Pols, kites & Gujarati thalis", ["cities", "heritage"]],
  lucknow: [S("sunset", "skyline", "city", "gateway", ["rickshaw", "kites"]), "🍢", "Nawabi food & monuments", ["cities", "heritage"]],
  chandigarh: [S("day", "hills", "city", null, ["birds"]), "🌳", "Gardens, lakes & the Rock Garden", ["cities"]],
  guwahati: [S("dusk", "hills", "river", null, ["rowboats", "birds"]), "🛶", "Gateway to the Northeast, on the Brahmaputra", ["cities", "spiritual"]],
  bhubaneswar: [S("dawn", "hills", "grass", "kalinga", ["birds"]), "🛕", "The temple city", ["heritage", "spiritual"]],
  indore: [S("day", "skyline", "city", null, ["rickshaw"]), "🍢", "India's street-food capital", ["cities"]],
  bhopal: [S("sunset", "hills", "lake", null, ["sailboat", "birds"]), "🌅", "The city of lakes", ["cities"]],
  patna: [S("dusk", "skyline", "river", null, ["rowboats"]), "🌉", "On the banks of the Ganga", ["cities"]],
  nagpur: [S("day", "skyline", "city", "stupa", ["rickshaw"], { ls: 0.8 }), "🍊", "Oranges & tiger reserves nearby", ["cities"]],
  coimbatore: [S("day", "hills", "city", null, ["birds"]), "🏞️", "Gateway to the Nilgiris", ["cities"]],
  thiruvananthapuram: [S("day", "palms", "city", "gopuram", ["birds"]), "🛕", "Temples, palaces & nearby beaches", ["cities", "heritage"]],

  // beaches & islands
  goa: [S("sunset", "none", "sea", "lighthouse", ["sailboat", "dolphins", "birds"], { lx: 760 }), "🌴", "Sun, sand & susegād", ["beaches"]],
  gokarna: [S("sunset", "hills", "sea", null, ["rowboats", "birds"]), "🏝️", "Quiet beaches & a temple town", ["beaches", "spiritual"]],
  varkala: [S("sunset", "hills", "sea", null, ["surfer", "rowboats"]), "🏄", "Cliff-top cafés & surf", ["beaches"]],
  kovalam: [S("sunset", "palms", "sea", "lighthouse", ["surfer", "rowboats"]), "🌊", "Crescent beaches & a lighthouse", ["beaches"]],
  puri: [S("dawn", "none", "sea", "kalinga", ["rowboats", "birds"]), "🌊", "Temple town by the sea", ["beaches", "spiritual"]],
  konark: [S("dawn", "none", "sand", "sunTemple", ["birds"]), "☀️", "The Sun Temple's stone chariot", ["heritage"]],
  digha: [S("day", "none", "sea", null, ["rowboats", "kites"]), "🌊", "Kolkata's favourite beach escape", ["beaches"]],
  visakhapatnam: [S("sunset", "hills", "sea", "lighthouse", ["sailboat", "birds"]), "🌊", "Hills that meet the sea", ["beaches", "cities"]],
  puducherry: [S("day", "none", "sea", "church", ["sailboat", "birds"]), "🥐", "French lanes & quiet beaches", ["beaches", "heritage"]],
  mahabalipuram: [S("sunset", "none", "sea", "shoreTemple", ["rowboats"]), "🗿", "Shore temples & rock carvings", ["beaches", "heritage"]],
  kanyakumari: [S("dawn", "none", "sea", "rockMemorial", ["rowboats", "birds"]), "🌅", "Sunrise where three seas meet", ["beaches", "spiritual"]],
  rameswaram: [S("day", "none", "sea", "gopuram", ["rowboats"]), "🛕", "Island temple & the Pamban bridge", ["spiritual", "beaches"]],
  "port blair": [S("day", "palms", "ocean", null, ["sailboat", "fish"]), "🐠", "Turquoise water & island history", ["beaches"]],
  "havelock island": [S("day", "palms", "ocean", null, ["fish", "dolphins"]), "🐠", "Radhanagar Beach & coral reefs", ["beaches"]],
  lakshadweep: [S("day", "palms", "ocean", null, ["fish", "sailboat"]), "🐬", "Lagoons & coral islands", ["beaches"]],
  diu: [S("sunset", "none", "sea", "lighthouse", ["rowboats", "birds"]), "🏖️", "Laid-back island by a Portuguese fort", ["beaches"]],

  // Kerala & backwaters
  kochi: [S("sunset", "palms", "backwater", "chineseNets", ["rowboats", "birds"]), "🎣", "Fishing nets & spice-scented lanes", ["backwaters", "heritage"]],
  alleppey: [S("day", "palms", "backwater", null, ["houseboat", "birds"]), "🛶", "Houseboats on the backwaters", ["backwaters"]],
  kumarakom: [S("sunset", "palms", "backwater", null, ["houseboat", "birds"]), "🦩", "Lakeside resorts & a bird sanctuary", ["backwaters"]],
  munnar: [S("dawn", "hills", "rows", null, ["birds"]), "🍃", "Rolling tea estates", ["mountains", "backwaters"]],
  thekkady: [S("day", "forest", "lake", null, ["rowboats", "birds"]), "🐘", "Periyar lake & spice gardens", ["wildlife", "backwaters"]],
  wayanad: [S("day", "forest", "grass", "waterfall", ["birds"]), "🌿", "Waterfalls, forests & caves", ["mountains", "wildlife"]],

  // mountains & hill stations
  manali: [S("day", "peaks", "grass", "pagoda", ["paraglider", "birds"], { lx: 760 }), "❄️", "Snow peaks & café hopping", ["mountains"]],
  shimla: [S("day", "peaks", "grass", "church", ["toyTrain", "birds"]), "🚂", "Toy train & colonial charm", ["mountains"]],
  kasol: [S("day", "peaks", "river", null, ["birds"]), "🏕️", "Riverside cafés in the Parvati valley", ["mountains"]],
  dharamshala: [S("day", "peaks", "grass", "monastery", ["prayerFlags", "paraglider"]), "🙏", "Monasteries & mountain views", ["mountains", "spiritual"]],
  dalhousie: [S("day", "peaks", "grass", "church", ["birds"]), "🌲", "Pine forests & old churches", ["mountains"]],
  spiti: [S("day", "barren", "rocky", "monastery", ["bike", "prayerFlags"]), "🏔️", "High-altitude desert monasteries", ["mountains"]],
  rishikesh: [S("day", "hills", "river", "jhula", ["raft", "birds"]), "🧘", "Ganga, yoga & rafting", ["mountains", "spiritual"]],
  haridwar: [S("dusk", "hills", "river", "ghats", ["diyas"]), "🪔", "Ganga aarti at Har Ki Pauri", ["spiritual"]],
  mussoorie: [S("day", "peaks", "grass", "hillTown", ["gondola", "birds"]), "⛰️", "The Queen of the Hills", ["mountains"]],
  nainital: [S("day", "hills", "lake", "hillTown", ["sailboat", "birds"]), "⛵", "Boating on Naini Lake", ["mountains"]],
  auli: [S("day", "peaks", "snow", null, ["skier", "gondola", "snow"]), "⛷️", "Ski slopes & Himalayan views", ["mountains"]],
  "jim corbett": [S("day", "forest", "grass", null, ["tiger", "elephant", "birds"]), "🐯", "Tiger safaris in the foothills", ["wildlife"]],
  srinagar: [S("day", "peaks", "lake", "houseboats", ["shikara"]), "🛶", "Shikaras on Dal Lake", ["mountains"]],
  gulmarg: [S("day", "peaks", "snow", null, ["gondola", "skier", "snow"]), "🚡", "Gondola rides & snowy meadows", ["mountains"]],
  pahalgam: [S("day", "peaks", "river", null, ["birds"]), "🏞️", "Valleys, rivers & meadows", ["mountains"]],
  leh: [S("day", "barren", "rocky", "monastery", ["bike", "prayerFlags"]), "🏍️", "High passes & blue skies", ["mountains"]],
  darjeeling: [S("dawn", "peaks", "rows", null, ["toyTrain"]), "🍵", "Tea gardens & Kanchenjunga sunrises", ["mountains"]],
  gangtok: [S("day", "peaks", "grass", "monastery", ["gondola", "prayerFlags"]), "🏔️", "Monasteries & mountain roads", ["mountains", "spiritual"]],
  tawang: [S("day", "peaks", "grass", "monastery", ["prayerFlags", "snow"]), "🏔️", "A great monastery above the clouds", ["mountains", "spiritual"]],
  shillong: [S("day", "hills", "lake", null, ["rowboats", "birds"]), "🌲", "Umiam Lake & pine-covered hills", ["mountains"]],
  cherrapunji: [S("day", "forest", "grass", "waterfall", ["rain"]), "🌧️", "Living-root bridges & rain", ["mountains"]],
  ooty: [S("day", "hills", "rows", null, ["toyTrain"]), "🚂", "Nilgiri toy train & tea", ["mountains"]],
  kodaikanal: [S("dawn", "hills", "lake", null, ["rowboats", "birds"]), "🌲", "Misty lake & pine forests", ["mountains"]],
  coorg: [S("day", "forest", "rows", "waterfall", ["birds"]), "☕", "Coffee estates & waterfalls", ["mountains"]],
  chikmagalur: [S("dawn", "hills", "rows", null, ["birds"]), "☕", "Coffee country in the hills", ["mountains"]],
  lonavala: [S("day", "hills", "grass", "caves", ["birds"], { ls: 0.8 }), "🌧️", "Monsoon hills & the Karla caves", ["mountains"]],
  mahabaleshwar: [S("sunset", "hills", "grass", null, ["birds"]), "🍓", "Strawberries & valley viewpoints", ["mountains"]],
  "mount abu": [S("sunset", "hills", "lake", null, ["rowboats", "birds"]), "⛰️", "Rajasthan's only hill station", ["mountains"]],

  // heritage
  jaipur: [S("dawn", "hills", "sand", "hawaMahal", ["balloons", "kites"]), "🏰", "Palaces in pink", ["heritage"]],
  udaipur: [S("sunset", "hills", "lake", "lakePalace", ["rowboats"]), "🏯", "Lakes & lit-up palaces", ["heritage"]],
  jodhpur: [S("day", "none", "sand", "blueFort", ["kites", "birds"]), "🔵", "The blue city under Mehrangarh", ["heritage"]],
  jaisalmer: [S("sunset", "dunes", "sand", "goldenFort", ["camels"], { lx: 780, ls: 0.8 }), "🐪", "Golden fort & desert dunes", ["heritage"]],
  pushkar: [S("sunset", "hills", "lake", "ghats", ["camels", "balloons"], { ls: 0.8 }), "🐪", "Holy lake, ghats & the camel fair", ["spiritual", "heritage"]],
  ranthambore: [S("day", "hills", "grass", "ruinFort", ["tiger"]), "🐯", "Tigers among fort ruins", ["wildlife", "heritage"]],
  agra: [S("dawn", "none", "river", "taj", ["birds"]), "🕌", "The Taj at sunrise", ["heritage"]],
  amritsar: [S("dusk", "none", "lake", "goldenTemple", ["birds"]), "✨", "The Golden Temple & langar", ["spiritual", "heritage"]],
  mysuru: [S("night", "none", "grass", "palace", []), "👑", "A palace that glows at night", ["heritage"]],
  hampi: [S("sunset", "none", "rocky", "gopuram", ["birds"]), "🪨", "Ruins among giant boulders", ["heritage"]],
  khajuraho: [S("dawn", "none", "grass", "khajuraho", ["birds"]), "🛕", "Temple spires carved in stone", ["heritage"]],
  aurangabad: [S("day", "none", "rocky", "caves", ["birds"]), "🏛️", "Ajanta & Ellora caves", ["heritage"]],
  madurai: [S("day", "none", "city", "gopuram", ["rickshaw"]), "🛕", "The Meenakshi temple towers", ["heritage", "spiritual"]],
  bhuj: [S("night", "none", "salt", null, ["camels"]), "🌙", "The white salt desert of Kutch", ["heritage"]],

  // spiritual
  varanasi: [S("dusk", "none", "river", "ghats", ["diyas", "rowboats"]), "🪔", "Ghats, aartis & old lanes", ["spiritual"]],
  ayodhya: [S("dusk", "none", "river", "nagara", ["diyas"]), "🪔", "Temple town on the Saryu", ["spiritual"]],
  mathura: [S("day", "none", "river", "ghats", ["rowboats", "birds"]), "🦚", "Krishna's birthplace & Vrindavan", ["spiritual"]],
  "bodh gaya": [S("dawn", "none", "grass", "mahabodhi", ["prayerFlags", "birds"]), "☸️", "Where the Buddha found enlightenment", ["spiritual", "heritage"]],
  ujjain: [S("night", "none", "river", "nagara", ["diyas"]), "🔱", "Mahakaleshwar & the Shipra ghats", ["spiritual"]],
  tirupati: [S("day", "hills", "grass", "gopuram", ["birds"]), "🛕", "The hill-top Venkateswara temple", ["spiritual"]],
  shirdi: [S("day", "none", "grass", "nagara", ["birds"]), "🙏", "Sai Baba's town", ["spiritual"]],
  nashik: [S("sunset", "hills", "rows", null, ["birds"]), "🍇", "Vineyards & the Godavari ghats", ["spiritual"]],
  dwarka: [S("sunset", "none", "sea", "nagara", ["rowboats"]), "🛕", "Krishna's temple by the sea", ["spiritual", "beaches"]],
  somnath: [S("day", "none", "sea", "nagara", ["rowboats", "birds"]), "🌊", "Where the temple meets the Arabian Sea", ["spiritual", "beaches"]],

  // wildlife
  kaziranga: [S("day", "forest", "grass", null, ["rhino", "elephant", "birds"]), "🦏", "One-horned rhinos in the grasslands", ["wildlife"]],
  gir: [S("day", "forest", "grass", null, ["lion", "birds"]), "🦁", "Home of the Asiatic lion", ["wildlife"]],
  sundarbans: [S("dusk", "forest", "backwater", null, ["rowboats", "birds"]), "🐅", "Mangrove creeks & tigers", ["wildlife", "backwaters"]],

  // abroad
  bali: [S("sunset", "hills", "rows", "splitGate", ["birds"]), "🌺", "Rice terraces, temples & surf", ["abroad", "beaches"]],
  dubai: [S("dusk", "dunes", "sand", "burj", ["camels"]), "🏙️", "Skyscrapers & desert dunes", ["abroad", "cities"]],
  bangkok: [S("sunset", "skyline", "river", "prang", ["rowboats"]), "🛺", "Street food & golden temples", ["abroad", "cities"]],
  singapore: [S("night", "skyline", "lake", "marinaBay", []), "🌃", "Gardens, hawkers & skyline", ["abroad", "cities"]],
  kathmandu: [S("day", "peaks", "grass", "stupa", ["prayerFlags", "birds"]), "🙏", "Stupas & Himalayan views", ["abroad", "mountains", "spiritual"]],
  male: [S("day", "none", "ocean", "waterVillas", ["fish", "dolphins"]), "🐬", "Overwater villas & lagoons", ["abroad", "beaches"]],
};

const DEFAULT_LOOK: Look = [S("day", "skyline", "city", null, ["birds"]), "🧭", "Your next adventure", ["cities"]];

const KIND_COLORS: Record<SceneKind, { accent: string; tint: string }> = {
  beach: { accent: "#0d8573", tint: "#effcf9" },
  hills: { accent: "#2f7fd8", tint: "#eff6ff" },
  heritage: { accent: "#c2417a", tint: "#fdf2f8" },
  river: { accent: "#c7801a", tint: "#fffbeb" },
  city: { accent: "#6d5bd0", tint: "#f5f3ff" },
};

function kindOf(tags: Tag[]): SceneKind {
  if (tags.includes("beaches") || tags.includes("backwaters")) return "beach";
  if (tags.includes("mountains")) return "hills";
  if (tags.includes("spiritual")) return "river";
  if (tags.includes("heritage")) return "heritage";
  return "city";
}

export function vibeFor(city: string | undefined): Vibe {
  const [spec, emoji, tagline, tags] = LOOKS[(city ?? "").trim().toLowerCase()] ?? DEFAULT_LOOK;
  const scene = kindOf(tags);
  return { spec, scene, emoji, tagline, tags, ...KIND_COLORS[scene] };
}

export const EXPLORE: { tag: Tag; label: string }[] = [
  { tag: "beaches", label: "🏖️ Beaches" },
  { tag: "mountains", label: "🏔️ Mountains" },
  { tag: "heritage", label: "🏰 Heritage" },
  { tag: "spiritual", label: "🪔 Spiritual" },
  { tag: "wildlife", label: "🐯 Wildlife" },
  { tag: "backwaters", label: "🛶 Kerala & backwaters" },
  { tag: "cities", label: "🏙️ Cities" },
  { tag: "abroad", label: "✈️ Abroad" },
];

/** Proper-cased destination names for a tag, in the order they're listed above. */
export function destinationsWith(tag: Tag): string[] {
  return Object.entries(LOOKS)
    .filter(([, look]) => look[3].includes(tag))
    .map(([key]) => key.replace(/\b\w/g, (c) => c.toUpperCase()));
}

// Shown while a plan is being built. General, practical, and true everywhere.
export const TRAVEL_TIPS = [
  "Indian Railways opens bookings 60 days ahead. Popular trains fill fast.",
  "Hotels are often cheaper Sunday to Thursday than on weekends.",
  "Keep a photo of your ID on your phone as well as the original.",
  "In a sleeper train, a lower berth doubles as a seat during the day.",
  "App cabs are usually cheaper than hailing a taxi near stations and airports.",
  "Carry a refillable water bottle. Many hotels and cafés will refill it.",
  "Visit popular sights right at opening time to beat the crowds and heat.",
  "Download offline maps before heading to the hills.",
  "Modest clothing (covered shoulders and knees) is expected in most temples.",
  "A power bank saves the day on long bus and train journeys.",
];
