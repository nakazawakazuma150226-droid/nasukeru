// Template repository boundary. Keep callers using getTemplates() so this file can be replaced by an API client later.
// ──────────────────────────────────────────────────────
// 脳梗塞テンプレートデータ  仕様書 Ver1 準拠
// ──────────────────────────────────────────────────────
var STROKE_TYPES = [
  {
    id: "mca", label: "MCA", full: "MCA領域梗塞（中大脳動脈）",
    vitals: { jcs:"", t:"", bp:"", hr:"", spo2:"" },
    symptoms: { headache:"", dizzy:"", nausea:"" },
    neuro: {
      pupil:"", light:"", eye:"",
      barre:"", mingazzini:"",
      mmt: { ru:"", rl:"", lu:"", ll:"" },
      nihss:"",
      other:""
    },
    rest: ""
  },
  {
    id: "aca", label: "ACA", full: "ACA領域梗塞（前大脳動脈）",
    vitals: { jcs:"", t:"", bp:"", hr:"", spo2:"" },
    symptoms: { headache:"", dizzy:"", nausea:"" },
    neuro: {
      pupil:"", light:"", eye:"",
      barre:"", mingazzini:"",
      mmt: { ru:"", rl:"", lu:"", ll:"" },
      nihss:"",
      other:""
    },
    rest: ""
  },
  {
    id: "pca", label: "PCA", full: "PCA領域梗塞（後大脳動脈）",
    vitals: { jcs:"", t:"", bp:"", hr:"", spo2:"" },
    symptoms: { headache:"", dizzy:"", nausea:"" },
    neuro: {
      pupil:"", light:"", eye:"",
      barre:"", mingazzini:"",
      mmt: { ru:"", rl:"", lu:"", ll:"" },
      nihss:"",
      other:""
    },
    rest: ""
  },
  {
    id: "lacunar", label: "ラクナ", full: "ラクナ梗塞／穿通枝梗塞",
    vitals: { jcs:"", t:"", bp:"", hr:"", spo2:"" },
    symptoms: { headache:"", dizzy:"", nausea:"" },
    neuro: {
      pupil:"", light:"", eye:"",
      barre:"", mingazzini:"",
      mmt: { ru:"", rl:"", lu:"", ll:"" },
      nihss:"",
      other:""
    },
    rest: ""
  },
  {
    id: "brainstem", label: "脳幹", full: "脳幹梗塞",
    vitals: { jcs:"", t:"", bp:"", hr:"", spo2:"" },
    symptoms: { headache:"", dizzy:"", nausea:"" },
    neuro: {
      pupil:"", light:"", eye:"",
      barre:"", mingazzini:"",
      mmt: { ru:"", rl:"", lu:"", ll:"" },
      nihss:"",
      other:""
    },
    rest: ""
  }
];

var REST_OPTS = ["ベッド上安静","ベッド上フリー","病棟内フリー","院内フリー","リハビリに準ずる"];
var QUICK_LIST = [
  { label:"脳梗塞", sub:"5パターン専用テンプレ", action:"stroke" }
];



async function getTemplates() {
  return STROKE_TYPES;
}

async function getQuickTemplates() {
  return QUICK_LIST;
}

async function getRestOptions() {
  return REST_OPTS;
}
