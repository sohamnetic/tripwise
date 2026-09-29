// A destination's scene is composed from a small kit of layers:
//   sky → far backdrop → ground → landmark (+ reflection on water) → moving things → foreground
// All drawing uses a 1200×400 viewBox with the horizon at y = HORIZON.

export const W = 1200;
export const H = 400;
export const HORIZON = 280;

export type Sky = "dawn" | "day" | "sunset" | "dusk" | "night";
export type Far = "peaks" | "barren" | "hills" | "dunes" | "skyline" | "forest" | "palms" | "none";
export type Ground =
  | "sea" | "ocean" | "lake" | "river" | "backwater"
  | "grass" | "snow" | "sand" | "city" | "rocky" | "salt" | "rows";

export type Landmark =
  | "taj" | "hawaMahal" | "indiaGate" | "gateway" | "howrah" | "charminar" | "goldenTemple"
  | "lakePalace" | "blueFort" | "goldenFort" | "ruinFort" | "palace" | "gopuram" | "kalinga"
  | "sunTemple" | "monastery" | "jhula" | "lighthouse" | "shoreTemple" | "mahabodhi"
  | "khajuraho" | "nagara" | "rockMemorial" | "church" | "hillTown" | "ghats" | "chineseNets"
  | "waterfall" | "caves" | "pagoda" | "houseboats" | "burj" | "marinaBay" | "prang"
  | "splitGate" | "stupa" | "waterVillas";

export type Motion =
  | "sailboat" | "rowboats" | "houseboat" | "shikara" | "raft" | "diyas" | "fish" | "dolphins"
  | "surfer" | "birds" | "kites" | "balloons" | "paraglider" | "gondola" | "snow" | "rain"
  | "toyTrain" | "camels" | "bike" | "rickshaw" | "rhino" | "elephant" | "tiger" | "lion"
  | "flamingos" | "skier" | "prayerFlags";

export interface SceneSpec {
  sky: Sky;
  far: Far;
  ground: Ground;
  landmark?: Landmark;
  motions: Motion[];
  lx?: number; // landmark centre x (default 700)
  ls?: number; // landmark scale (default 1)
}

export const WATER: ReadonlySet<Ground> = new Set(["sea", "ocean", "lake", "river", "backwater"]);
// water still enough to show a reflection
export const REFLECTS: ReadonlySet<Ground> = new Set(["lake", "river", "backwater"]);
