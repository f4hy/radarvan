/* eslint-disable */
import { Timestamp } from "../google/protobuf/timestamp"
import Long from "long"
import _m0 from "protobufjs/minimal"

export const protobufPackage = "matches"

export enum General {
  USA = 0,
  AIR = 1,
  LASER = 2,
  SUPER = 3,
  CHINA = 4,
  NUKE = 5,
  TANK = 6,
  INFANTRY = 7,
  GLA = 8,
  TOXIN = 9,
  STEALTH = 10,
  DEMO = 11,
  UNRECOGNIZED = -1,
}

export function generalFromJSON(object: any): General {
  switch (object) {
    case 0:
    case "USA":
      return General.USA
    case 1:
    case "AIR":
      return General.AIR
    case 2:
    case "LASER":
      return General.LASER
    case 3:
    case "SUPER":
      return General.SUPER
    case 4:
    case "CHINA":
      return General.CHINA
    case 5:
    case "NUKE":
      return General.NUKE
    case 6:
    case "TANK":
      return General.TANK
    case 7:
    case "INFANTRY":
      return General.INFANTRY
    case 8:
    case "GLA":
      return General.GLA
    case 9:
    case "TOXIN":
      return General.TOXIN
    case 10:
    case "STEALTH":
      return General.STEALTH
    case 11:
    case "DEMO":
      return General.DEMO
    case -1:
    case "UNRECOGNIZED":
    default:
      return General.UNRECOGNIZED
  }
}

export function generalToJSON(object: General): string {
  switch (object) {
    case General.USA:
      return "USA"
    case General.AIR:
      return "AIR"
    case General.LASER:
      return "LASER"
    case General.SUPER:
      return "SUPER"
    case General.CHINA:
      return "CHINA"
    case General.NUKE:
      return "NUKE"
    case General.TANK:
      return "TANK"
    case General.INFANTRY:
      return "INFANTRY"
    case General.GLA:
      return "GLA"
    case General.TOXIN:
      return "TOXIN"
    case General.STEALTH:
      return "STEALTH"
    case General.DEMO:
      return "DEMO"
    case General.UNRECOGNIZED:
    default:
      return "UNRECOGNIZED"
  }
}

export enum Faction {
  ANYUSA = 0,
  ANYCHINA = 1,
  ANYGLA = 2,
  UNRECOGNIZED = -1,
}

export function factionFromJSON(object: any): Faction {
  switch (object) {
    case 0:
    case "ANYUSA":
      return Faction.ANYUSA
    case 1:
    case "ANYCHINA":
      return Faction.ANYCHINA
    case 2:
    case "ANYGLA":
      return Faction.ANYGLA
    case -1:
    case "UNRECOGNIZED":
    default:
      return Faction.UNRECOGNIZED
  }
}

export function factionToJSON(object: Faction): string {
  switch (object) {
    case Faction.ANYUSA:
      return "ANYUSA"
    case Faction.ANYCHINA:
      return "ANYCHINA"
    case Faction.ANYGLA:
      return "ANYGLA"
    case Faction.UNRECOGNIZED:
    default:
      return "UNRECOGNIZED"
  }
}

export enum Team {
  NONE = 0,
  ONE = 1,
  TWO = 2,
  THREE = 3,
  FOUR = 4,
  UNRECOGNIZED = -1,
}

export function teamFromJSON(object: any): Team {
  switch (object) {
    case 0:
    case "NONE":
      return Team.NONE
    case 1:
    case "ONE":
      return Team.ONE
    case 2:
    case "TWO":
      return Team.TWO
    case 3:
    case "THREE":
      return Team.THREE
    case 4:
    case "FOUR":
      return Team.FOUR
    case -1:
    case "UNRECOGNIZED":
    default:
      return Team.UNRECOGNIZED
  }
}

export function teamToJSON(object: Team): string {
  switch (object) {
    case Team.NONE:
      return "NONE"
    case Team.ONE:
      return "ONE"
    case Team.TWO:
      return "TWO"
    case Team.THREE:
      return "THREE"
    case Team.FOUR:
      return "FOUR"
    case Team.UNRECOGNIZED:
    default:
      return "UNRECOGNIZED"
  }
}

export interface Player {
  name: string
  general: General
  team: Team
}

export interface MatchInfo {
  id: number
  timestamp: Date | undefined
  map: string
  winningTeam: Team
  players: Player[]
  durationMinutes: number
  filename: string
  incomplete: string
  notes: string
}

export interface Matches {
  matches: MatchInfo[]
}

export interface WinLoss {
  wins: number
  losses: number
}

export interface GeneralWL {
  general: General
  winLoss: WinLoss | undefined
}

export interface PlayerRateOverTime {
  date: DateMessage | undefined
  wl: GeneralWL | undefined
}

export interface PlayerStat {
  playerName: string
  stats: GeneralWL[]
  factionStats: PlayerStat_FactionWL[]
  overTime: PlayerRateOverTime[]
}

export interface PlayerStat_FactionWL {
  faction: Faction
  winLoss: WinLoss | undefined
}

export interface PlayerStats {
  playerStats: PlayerStat[]
}

export interface GeneralStat {
  general: General
  stats: GeneralStat_PlayerWL[]
  total: WinLoss | undefined
}

export interface GeneralStat_PlayerWL {
  playerName: string
  winLoss: WinLoss | undefined
}

export interface GeneralStats {
  generalStats: GeneralStat[]
}

export interface DateMessage {
  Year: number
  Month: number
  Day: number
}

export interface TeamStat {
  date: DateMessage | undefined
  team: Team
  wins: number
}

export interface TeamStats {
  teamStats: TeamStat[]
}

export interface MapStat {
  map: string
  team: Team
  wins: number
}

export interface MapResult {
  map: string
  date: DateMessage | undefined
  winner: Team
}

export interface MapResults {
  results: MapResult[]
}

export interface MapStats {
  mapStats: MapStat[]
  overTime: { [key: string]: MapResults }
}

export interface MapStats_OverTimeEntry {
  key: string
  value: MapResults | undefined
}

export interface SaveResponse {
  success: boolean
}

export interface Costs {
  player: Player | undefined
  buildings: Costs_BuiltObject[]
  units: Costs_BuiltObject[]
  upgrades: Costs_BuiltObject[]
}

export interface Costs_BuiltObject {
  name: string
  count: number
  totalSpent: number
}

export interface APM {
  playerName: string
  actionCount: number
  minutes: number
  apm: number
}

export interface UpgradeEvent {
  playerName: string
  timecode: number
  upgradeName: string
  cost: number
  atMinute: number
}

export interface Spent {
  playerName: string
  accCost: number
  atMinute: number
}

export interface Upgrades {
  upgrades: UpgradeEvent[]
}

export interface SpentOverTime {
  buildings: Spent[]
  units: Spent[]
  upgrades: Spent[]
  total: Spent[]
}

export interface MatchDetails {
  matchId: number
  costs: Costs[]
  apms: APM[]
  upgradeEvents: { [key: string]: Upgrades }
  spent: SpentOverTime | undefined
}

export interface MatchDetails_UpgradeEventsEntry {
  key: string
  value: Upgrades | undefined
}

export interface PairWinLoss {
  general1: General
  general2: General
  winloss: WinLoss | undefined
}

export interface PairFactionWinLoss {
  faction1: Faction
  faction2: Faction
  winloss: WinLoss | undefined
}

export interface PairsWinLosses {
  pairwl: PairWinLoss[]
}

export interface PairFactionWinLosses {
  pairwl: PairFactionWinLoss[]
}

export interface TeamPairs {
  teamPairs: { [key: string]: PairsWinLosses }
  factionPairs: { [key: string]: PairFactionWinLosses }
}

export interface TeamPairs_TeamPairsEntry {
  key: string
  value: PairsWinLosses | undefined
}

export interface TeamPairs_FactionPairsEntry {
  key: string
  value: PairFactionWinLosses | undefined
}

export interface Wrapped {
  gamesPlayed: number
  hoursPlayed: number
  mostPlayed: General
  mostPlayedWinrate: number
  mostBuilt: string
  mostBuiltSpent: number
  mostBuiltCount: number
  mostBuiltMore: number
  bestGeneral: General
  bestWinrate: number
  bestAverage: number
}

function createBasePlayer(): Player {
  return { name: "", general: 0, team: 0 }
}

export const Player = {
  encode(
    message: Player,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    if (message.name !== "") {
      writer.uint32(10).string(message.name)
    }
    if (message.general !== 0) {
      writer.uint32(16).int32(message.general)
    }
    if (message.team !== 0) {
      writer.uint32(24).int32(message.team)
    }
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): Player {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBasePlayer()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.name = reader.string()
          break
        case 2:
          message.general = reader.int32() as any
          break
        case 3:
          message.team = reader.int32() as any
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): Player {
    return {
      name: isSet(object.name) ? String(object.name) : "",
      general: isSet(object.general) ? generalFromJSON(object.general) : 0,
      team: isSet(object.team) ? teamFromJSON(object.team) : 0,
    }
  },

  toJSON(message: Player): unknown {
    const obj: any = {}
    message.name !== undefined && (obj.name = message.name)
    message.general !== undefined &&
      (obj.general = generalToJSON(message.general))
    message.team !== undefined && (obj.team = teamToJSON(message.team))
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<Player>, I>>(object: I): Player {
    const message = createBasePlayer()
    message.name = object.name ?? ""
    message.general = object.general ?? 0
    message.team = object.team ?? 0
    return message
  },
}

function createBaseMatchInfo(): MatchInfo {
  return {
    id: 0,
    timestamp: undefined,
    map: "",
    winningTeam: 0,
    players: [],
    durationMinutes: 0,
    filename: "",
    incomplete: "",
    notes: "",
  }
}

export const MatchInfo = {
  encode(
    message: MatchInfo,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    if (message.id !== 0) {
      writer.uint32(8).int64(message.id)
    }
    if (message.timestamp !== undefined) {
      Timestamp.encode(
        toTimestamp(message.timestamp),
        writer.uint32(18).fork()
      ).ldelim()
    }
    if (message.map !== "") {
      writer.uint32(26).string(message.map)
    }
    if (message.winningTeam !== 0) {
      writer.uint32(32).int32(message.winningTeam)
    }
    for (const v of message.players) {
      Player.encode(v!, writer.uint32(42).fork()).ldelim()
    }
    if (message.durationMinutes !== 0) {
      writer.uint32(49).double(message.durationMinutes)
    }
    if (message.filename !== "") {
      writer.uint32(58).string(message.filename)
    }
    if (message.incomplete !== "") {
      writer.uint32(66).string(message.incomplete)
    }
    if (message.notes !== "") {
      writer.uint32(74).string(message.notes)
    }
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): MatchInfo {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBaseMatchInfo()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.id = longToNumber(reader.int64() as Long)
          break
        case 2:
          message.timestamp = fromTimestamp(
            Timestamp.decode(reader, reader.uint32())
          )
          break
        case 3:
          message.map = reader.string()
          break
        case 4:
          message.winningTeam = reader.int32() as any
          break
        case 5:
          message.players.push(Player.decode(reader, reader.uint32()))
          break
        case 6:
          message.durationMinutes = reader.double()
          break
        case 7:
          message.filename = reader.string()
          break
        case 8:
          message.incomplete = reader.string()
          break
        case 9:
          message.notes = reader.string()
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): MatchInfo {
    return {
      id: isSet(object.id) ? Number(object.id) : 0,
      timestamp: isSet(object.timestamp)
        ? fromJsonTimestamp(object.timestamp)
        : undefined,
      map: isSet(object.map) ? String(object.map) : "",
      winningTeam: isSet(object.winningTeam)
        ? teamFromJSON(object.winningTeam)
        : 0,
      players: Array.isArray(object?.players)
        ? object.players.map((e: any) => Player.fromJSON(e))
        : [],
      durationMinutes: isSet(object.durationMinutes)
        ? Number(object.durationMinutes)
        : 0,
      filename: isSet(object.filename) ? String(object.filename) : "",
      incomplete: isSet(object.incomplete) ? String(object.incomplete) : "",
      notes: isSet(object.notes) ? String(object.notes) : "",
    }
  },

  toJSON(message: MatchInfo): unknown {
    const obj: any = {}
    message.id !== undefined && (obj.id = Math.round(message.id))
    message.timestamp !== undefined &&
      (obj.timestamp = message.timestamp.toISOString())
    message.map !== undefined && (obj.map = message.map)
    message.winningTeam !== undefined &&
      (obj.winningTeam = teamToJSON(message.winningTeam))
    if (message.players) {
      obj.players = message.players.map((e) =>
        e ? Player.toJSON(e) : undefined
      )
    } else {
      obj.players = []
    }
    message.durationMinutes !== undefined &&
      (obj.durationMinutes = message.durationMinutes)
    message.filename !== undefined && (obj.filename = message.filename)
    message.incomplete !== undefined && (obj.incomplete = message.incomplete)
    message.notes !== undefined && (obj.notes = message.notes)
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<MatchInfo>, I>>(
    object: I
  ): MatchInfo {
    const message = createBaseMatchInfo()
    message.id = object.id ?? 0
    message.timestamp = object.timestamp ?? undefined
    message.map = object.map ?? ""
    message.winningTeam = object.winningTeam ?? 0
    message.players = object.players?.map((e) => Player.fromPartial(e)) || []
    message.durationMinutes = object.durationMinutes ?? 0
    message.filename = object.filename ?? ""
    message.incomplete = object.incomplete ?? ""
    message.notes = object.notes ?? ""
    return message
  },
}

function createBaseMatches(): Matches {
  return { matches: [] }
}

export const Matches = {
  encode(
    message: Matches,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    for (const v of message.matches) {
      MatchInfo.encode(v!, writer.uint32(10).fork()).ldelim()
    }
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): Matches {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBaseMatches()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.matches.push(MatchInfo.decode(reader, reader.uint32()))
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): Matches {
    return {
      matches: Array.isArray(object?.matches)
        ? object.matches.map((e: any) => MatchInfo.fromJSON(e))
        : [],
    }
  },

  toJSON(message: Matches): unknown {
    const obj: any = {}
    if (message.matches) {
      obj.matches = message.matches.map((e) =>
        e ? MatchInfo.toJSON(e) : undefined
      )
    } else {
      obj.matches = []
    }
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<Matches>, I>>(object: I): Matches {
    const message = createBaseMatches()
    message.matches = object.matches?.map((e) => MatchInfo.fromPartial(e)) || []
    return message
  },
}

function createBaseWinLoss(): WinLoss {
  return { wins: 0, losses: 0 }
}

export const WinLoss = {
  encode(
    message: WinLoss,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    if (message.wins !== 0) {
      writer.uint32(8).int32(message.wins)
    }
    if (message.losses !== 0) {
      writer.uint32(16).int32(message.losses)
    }
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): WinLoss {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBaseWinLoss()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.wins = reader.int32()
          break
        case 2:
          message.losses = reader.int32()
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): WinLoss {
    return {
      wins: isSet(object.wins) ? Number(object.wins) : 0,
      losses: isSet(object.losses) ? Number(object.losses) : 0,
    }
  },

  toJSON(message: WinLoss): unknown {
    const obj: any = {}
    message.wins !== undefined && (obj.wins = Math.round(message.wins))
    message.losses !== undefined && (obj.losses = Math.round(message.losses))
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<WinLoss>, I>>(object: I): WinLoss {
    const message = createBaseWinLoss()
    message.wins = object.wins ?? 0
    message.losses = object.losses ?? 0
    return message
  },
}

function createBaseGeneralWL(): GeneralWL {
  return { general: 0, winLoss: undefined }
}

export const GeneralWL = {
  encode(
    message: GeneralWL,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    if (message.general !== 0) {
      writer.uint32(8).int32(message.general)
    }
    if (message.winLoss !== undefined) {
      WinLoss.encode(message.winLoss, writer.uint32(18).fork()).ldelim()
    }
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): GeneralWL {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBaseGeneralWL()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.general = reader.int32() as any
          break
        case 2:
          message.winLoss = WinLoss.decode(reader, reader.uint32())
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): GeneralWL {
    return {
      general: isSet(object.general) ? generalFromJSON(object.general) : 0,
      winLoss: isSet(object.winLoss)
        ? WinLoss.fromJSON(object.winLoss)
        : undefined,
    }
  },

  toJSON(message: GeneralWL): unknown {
    const obj: any = {}
    message.general !== undefined &&
      (obj.general = generalToJSON(message.general))
    message.winLoss !== undefined &&
      (obj.winLoss = message.winLoss
        ? WinLoss.toJSON(message.winLoss)
        : undefined)
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<GeneralWL>, I>>(
    object: I
  ): GeneralWL {
    const message = createBaseGeneralWL()
    message.general = object.general ?? 0
    message.winLoss =
      object.winLoss !== undefined && object.winLoss !== null
        ? WinLoss.fromPartial(object.winLoss)
        : undefined
    return message
  },
}

function createBasePlayerRateOverTime(): PlayerRateOverTime {
  return { date: undefined, wl: undefined }
}

export const PlayerRateOverTime = {
  encode(
    message: PlayerRateOverTime,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    if (message.date !== undefined) {
      DateMessage.encode(message.date, writer.uint32(10).fork()).ldelim()
    }
    if (message.wl !== undefined) {
      GeneralWL.encode(message.wl, writer.uint32(18).fork()).ldelim()
    }
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): PlayerRateOverTime {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBasePlayerRateOverTime()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.date = DateMessage.decode(reader, reader.uint32())
          break
        case 2:
          message.wl = GeneralWL.decode(reader, reader.uint32())
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): PlayerRateOverTime {
    return {
      date: isSet(object.date) ? DateMessage.fromJSON(object.date) : undefined,
      wl: isSet(object.wl) ? GeneralWL.fromJSON(object.wl) : undefined,
    }
  },

  toJSON(message: PlayerRateOverTime): unknown {
    const obj: any = {}
    message.date !== undefined &&
      (obj.date = message.date ? DateMessage.toJSON(message.date) : undefined)
    message.wl !== undefined &&
      (obj.wl = message.wl ? GeneralWL.toJSON(message.wl) : undefined)
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<PlayerRateOverTime>, I>>(
    object: I
  ): PlayerRateOverTime {
    const message = createBasePlayerRateOverTime()
    message.date =
      object.date !== undefined && object.date !== null
        ? DateMessage.fromPartial(object.date)
        : undefined
    message.wl =
      object.wl !== undefined && object.wl !== null
        ? GeneralWL.fromPartial(object.wl)
        : undefined
    return message
  },
}

function createBasePlayerStat(): PlayerStat {
  return { playerName: "", stats: [], factionStats: [], overTime: [] }
}

export const PlayerStat = {
  encode(
    message: PlayerStat,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    if (message.playerName !== "") {
      writer.uint32(10).string(message.playerName)
    }
    for (const v of message.stats) {
      GeneralWL.encode(v!, writer.uint32(18).fork()).ldelim()
    }
    for (const v of message.factionStats) {
      PlayerStat_FactionWL.encode(v!, writer.uint32(26).fork()).ldelim()
    }
    for (const v of message.overTime) {
      PlayerRateOverTime.encode(v!, writer.uint32(34).fork()).ldelim()
    }
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): PlayerStat {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBasePlayerStat()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.playerName = reader.string()
          break
        case 2:
          message.stats.push(GeneralWL.decode(reader, reader.uint32()))
          break
        case 3:
          message.factionStats.push(
            PlayerStat_FactionWL.decode(reader, reader.uint32())
          )
          break
        case 4:
          message.overTime.push(
            PlayerRateOverTime.decode(reader, reader.uint32())
          )
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): PlayerStat {
    return {
      playerName: isSet(object.playerName) ? String(object.playerName) : "",
      stats: Array.isArray(object?.stats)
        ? object.stats.map((e: any) => GeneralWL.fromJSON(e))
        : [],
      factionStats: Array.isArray(object?.factionStats)
        ? object.factionStats.map((e: any) => PlayerStat_FactionWL.fromJSON(e))
        : [],
      overTime: Array.isArray(object?.overTime)
        ? object.overTime.map((e: any) => PlayerRateOverTime.fromJSON(e))
        : [],
    }
  },

  toJSON(message: PlayerStat): unknown {
    const obj: any = {}
    message.playerName !== undefined && (obj.playerName = message.playerName)
    if (message.stats) {
      obj.stats = message.stats.map((e) =>
        e ? GeneralWL.toJSON(e) : undefined
      )
    } else {
      obj.stats = []
    }
    if (message.factionStats) {
      obj.factionStats = message.factionStats.map((e) =>
        e ? PlayerStat_FactionWL.toJSON(e) : undefined
      )
    } else {
      obj.factionStats = []
    }
    if (message.overTime) {
      obj.overTime = message.overTime.map((e) =>
        e ? PlayerRateOverTime.toJSON(e) : undefined
      )
    } else {
      obj.overTime = []
    }
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<PlayerStat>, I>>(
    object: I
  ): PlayerStat {
    const message = createBasePlayerStat()
    message.playerName = object.playerName ?? ""
    message.stats = object.stats?.map((e) => GeneralWL.fromPartial(e)) || []
    message.factionStats =
      object.factionStats?.map((e) => PlayerStat_FactionWL.fromPartial(e)) || []
    message.overTime =
      object.overTime?.map((e) => PlayerRateOverTime.fromPartial(e)) || []
    return message
  },
}

function createBasePlayerStat_FactionWL(): PlayerStat_FactionWL {
  return { faction: 0, winLoss: undefined }
}

export const PlayerStat_FactionWL = {
  encode(
    message: PlayerStat_FactionWL,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    if (message.faction !== 0) {
      writer.uint32(8).int32(message.faction)
    }
    if (message.winLoss !== undefined) {
      WinLoss.encode(message.winLoss, writer.uint32(18).fork()).ldelim()
    }
    return writer
  },

  decode(
    input: _m0.Reader | Uint8Array,
    length?: number
  ): PlayerStat_FactionWL {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBasePlayerStat_FactionWL()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.faction = reader.int32() as any
          break
        case 2:
          message.winLoss = WinLoss.decode(reader, reader.uint32())
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): PlayerStat_FactionWL {
    return {
      faction: isSet(object.faction) ? factionFromJSON(object.faction) : 0,
      winLoss: isSet(object.winLoss)
        ? WinLoss.fromJSON(object.winLoss)
        : undefined,
    }
  },

  toJSON(message: PlayerStat_FactionWL): unknown {
    const obj: any = {}
    message.faction !== undefined &&
      (obj.faction = factionToJSON(message.faction))
    message.winLoss !== undefined &&
      (obj.winLoss = message.winLoss
        ? WinLoss.toJSON(message.winLoss)
        : undefined)
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<PlayerStat_FactionWL>, I>>(
    object: I
  ): PlayerStat_FactionWL {
    const message = createBasePlayerStat_FactionWL()
    message.faction = object.faction ?? 0
    message.winLoss =
      object.winLoss !== undefined && object.winLoss !== null
        ? WinLoss.fromPartial(object.winLoss)
        : undefined
    return message
  },
}

function createBasePlayerStats(): PlayerStats {
  return { playerStats: [] }
}

export const PlayerStats = {
  encode(
    message: PlayerStats,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    for (const v of message.playerStats) {
      PlayerStat.encode(v!, writer.uint32(10).fork()).ldelim()
    }
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): PlayerStats {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBasePlayerStats()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.playerStats.push(PlayerStat.decode(reader, reader.uint32()))
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): PlayerStats {
    return {
      playerStats: Array.isArray(object?.playerStats)
        ? object.playerStats.map((e: any) => PlayerStat.fromJSON(e))
        : [],
    }
  },

  toJSON(message: PlayerStats): unknown {
    const obj: any = {}
    if (message.playerStats) {
      obj.playerStats = message.playerStats.map((e) =>
        e ? PlayerStat.toJSON(e) : undefined
      )
    } else {
      obj.playerStats = []
    }
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<PlayerStats>, I>>(
    object: I
  ): PlayerStats {
    const message = createBasePlayerStats()
    message.playerStats =
      object.playerStats?.map((e) => PlayerStat.fromPartial(e)) || []
    return message
  },
}

function createBaseGeneralStat(): GeneralStat {
  return { general: 0, stats: [], total: undefined }
}

export const GeneralStat = {
  encode(
    message: GeneralStat,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    if (message.general !== 0) {
      writer.uint32(8).int32(message.general)
    }
    for (const v of message.stats) {
      GeneralStat_PlayerWL.encode(v!, writer.uint32(18).fork()).ldelim()
    }
    if (message.total !== undefined) {
      WinLoss.encode(message.total, writer.uint32(26).fork()).ldelim()
    }
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): GeneralStat {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBaseGeneralStat()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.general = reader.int32() as any
          break
        case 2:
          message.stats.push(
            GeneralStat_PlayerWL.decode(reader, reader.uint32())
          )
          break
        case 3:
          message.total = WinLoss.decode(reader, reader.uint32())
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): GeneralStat {
    return {
      general: isSet(object.general) ? generalFromJSON(object.general) : 0,
      stats: Array.isArray(object?.stats)
        ? object.stats.map((e: any) => GeneralStat_PlayerWL.fromJSON(e))
        : [],
      total: isSet(object.total) ? WinLoss.fromJSON(object.total) : undefined,
    }
  },

  toJSON(message: GeneralStat): unknown {
    const obj: any = {}
    message.general !== undefined &&
      (obj.general = generalToJSON(message.general))
    if (message.stats) {
      obj.stats = message.stats.map((e) =>
        e ? GeneralStat_PlayerWL.toJSON(e) : undefined
      )
    } else {
      obj.stats = []
    }
    message.total !== undefined &&
      (obj.total = message.total ? WinLoss.toJSON(message.total) : undefined)
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<GeneralStat>, I>>(
    object: I
  ): GeneralStat {
    const message = createBaseGeneralStat()
    message.general = object.general ?? 0
    message.stats =
      object.stats?.map((e) => GeneralStat_PlayerWL.fromPartial(e)) || []
    message.total =
      object.total !== undefined && object.total !== null
        ? WinLoss.fromPartial(object.total)
        : undefined
    return message
  },
}

function createBaseGeneralStat_PlayerWL(): GeneralStat_PlayerWL {
  return { playerName: "", winLoss: undefined }
}

export const GeneralStat_PlayerWL = {
  encode(
    message: GeneralStat_PlayerWL,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    if (message.playerName !== "") {
      writer.uint32(10).string(message.playerName)
    }
    if (message.winLoss !== undefined) {
      WinLoss.encode(message.winLoss, writer.uint32(18).fork()).ldelim()
    }
    return writer
  },

  decode(
    input: _m0.Reader | Uint8Array,
    length?: number
  ): GeneralStat_PlayerWL {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBaseGeneralStat_PlayerWL()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.playerName = reader.string()
          break
        case 2:
          message.winLoss = WinLoss.decode(reader, reader.uint32())
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): GeneralStat_PlayerWL {
    return {
      playerName: isSet(object.playerName) ? String(object.playerName) : "",
      winLoss: isSet(object.winLoss)
        ? WinLoss.fromJSON(object.winLoss)
        : undefined,
    }
  },

  toJSON(message: GeneralStat_PlayerWL): unknown {
    const obj: any = {}
    message.playerName !== undefined && (obj.playerName = message.playerName)
    message.winLoss !== undefined &&
      (obj.winLoss = message.winLoss
        ? WinLoss.toJSON(message.winLoss)
        : undefined)
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<GeneralStat_PlayerWL>, I>>(
    object: I
  ): GeneralStat_PlayerWL {
    const message = createBaseGeneralStat_PlayerWL()
    message.playerName = object.playerName ?? ""
    message.winLoss =
      object.winLoss !== undefined && object.winLoss !== null
        ? WinLoss.fromPartial(object.winLoss)
        : undefined
    return message
  },
}

function createBaseGeneralStats(): GeneralStats {
  return { generalStats: [] }
}

export const GeneralStats = {
  encode(
    message: GeneralStats,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    for (const v of message.generalStats) {
      GeneralStat.encode(v!, writer.uint32(10).fork()).ldelim()
    }
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): GeneralStats {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBaseGeneralStats()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.generalStats.push(GeneralStat.decode(reader, reader.uint32()))
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): GeneralStats {
    return {
      generalStats: Array.isArray(object?.generalStats)
        ? object.generalStats.map((e: any) => GeneralStat.fromJSON(e))
        : [],
    }
  },

  toJSON(message: GeneralStats): unknown {
    const obj: any = {}
    if (message.generalStats) {
      obj.generalStats = message.generalStats.map((e) =>
        e ? GeneralStat.toJSON(e) : undefined
      )
    } else {
      obj.generalStats = []
    }
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<GeneralStats>, I>>(
    object: I
  ): GeneralStats {
    const message = createBaseGeneralStats()
    message.generalStats =
      object.generalStats?.map((e) => GeneralStat.fromPartial(e)) || []
    return message
  },
}

function createBaseDateMessage(): DateMessage {
  return { Year: 0, Month: 0, Day: 0 }
}

export const DateMessage = {
  encode(
    message: DateMessage,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    if (message.Year !== 0) {
      writer.uint32(8).int32(message.Year)
    }
    if (message.Month !== 0) {
      writer.uint32(16).int32(message.Month)
    }
    if (message.Day !== 0) {
      writer.uint32(24).int32(message.Day)
    }
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): DateMessage {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBaseDateMessage()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.Year = reader.int32()
          break
        case 2:
          message.Month = reader.int32()
          break
        case 3:
          message.Day = reader.int32()
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): DateMessage {
    return {
      Year: isSet(object.Year) ? Number(object.Year) : 0,
      Month: isSet(object.Month) ? Number(object.Month) : 0,
      Day: isSet(object.Day) ? Number(object.Day) : 0,
    }
  },

  toJSON(message: DateMessage): unknown {
    const obj: any = {}
    message.Year !== undefined && (obj.Year = Math.round(message.Year))
    message.Month !== undefined && (obj.Month = Math.round(message.Month))
    message.Day !== undefined && (obj.Day = Math.round(message.Day))
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<DateMessage>, I>>(
    object: I
  ): DateMessage {
    const message = createBaseDateMessage()
    message.Year = object.Year ?? 0
    message.Month = object.Month ?? 0
    message.Day = object.Day ?? 0
    return message
  },
}

function createBaseTeamStat(): TeamStat {
  return { date: undefined, team: 0, wins: 0 }
}

export const TeamStat = {
  encode(
    message: TeamStat,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    if (message.date !== undefined) {
      DateMessage.encode(message.date, writer.uint32(10).fork()).ldelim()
    }
    if (message.team !== 0) {
      writer.uint32(16).int32(message.team)
    }
    if (message.wins !== 0) {
      writer.uint32(24).int32(message.wins)
    }
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): TeamStat {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBaseTeamStat()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.date = DateMessage.decode(reader, reader.uint32())
          break
        case 2:
          message.team = reader.int32() as any
          break
        case 3:
          message.wins = reader.int32()
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): TeamStat {
    return {
      date: isSet(object.date) ? DateMessage.fromJSON(object.date) : undefined,
      team: isSet(object.team) ? teamFromJSON(object.team) : 0,
      wins: isSet(object.wins) ? Number(object.wins) : 0,
    }
  },

  toJSON(message: TeamStat): unknown {
    const obj: any = {}
    message.date !== undefined &&
      (obj.date = message.date ? DateMessage.toJSON(message.date) : undefined)
    message.team !== undefined && (obj.team = teamToJSON(message.team))
    message.wins !== undefined && (obj.wins = Math.round(message.wins))
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<TeamStat>, I>>(object: I): TeamStat {
    const message = createBaseTeamStat()
    message.date =
      object.date !== undefined && object.date !== null
        ? DateMessage.fromPartial(object.date)
        : undefined
    message.team = object.team ?? 0
    message.wins = object.wins ?? 0
    return message
  },
}

function createBaseTeamStats(): TeamStats {
  return { teamStats: [] }
}

export const TeamStats = {
  encode(
    message: TeamStats,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    for (const v of message.teamStats) {
      TeamStat.encode(v!, writer.uint32(10).fork()).ldelim()
    }
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): TeamStats {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBaseTeamStats()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.teamStats.push(TeamStat.decode(reader, reader.uint32()))
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): TeamStats {
    return {
      teamStats: Array.isArray(object?.teamStats)
        ? object.teamStats.map((e: any) => TeamStat.fromJSON(e))
        : [],
    }
  },

  toJSON(message: TeamStats): unknown {
    const obj: any = {}
    if (message.teamStats) {
      obj.teamStats = message.teamStats.map((e) =>
        e ? TeamStat.toJSON(e) : undefined
      )
    } else {
      obj.teamStats = []
    }
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<TeamStats>, I>>(
    object: I
  ): TeamStats {
    const message = createBaseTeamStats()
    message.teamStats =
      object.teamStats?.map((e) => TeamStat.fromPartial(e)) || []
    return message
  },
}

function createBaseMapStat(): MapStat {
  return { map: "", team: 0, wins: 0 }
}

export const MapStat = {
  encode(
    message: MapStat,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    if (message.map !== "") {
      writer.uint32(10).string(message.map)
    }
    if (message.team !== 0) {
      writer.uint32(16).int32(message.team)
    }
    if (message.wins !== 0) {
      writer.uint32(24).int32(message.wins)
    }
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): MapStat {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBaseMapStat()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.map = reader.string()
          break
        case 2:
          message.team = reader.int32() as any
          break
        case 3:
          message.wins = reader.int32()
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): MapStat {
    return {
      map: isSet(object.map) ? String(object.map) : "",
      team: isSet(object.team) ? teamFromJSON(object.team) : 0,
      wins: isSet(object.wins) ? Number(object.wins) : 0,
    }
  },

  toJSON(message: MapStat): unknown {
    const obj: any = {}
    message.map !== undefined && (obj.map = message.map)
    message.team !== undefined && (obj.team = teamToJSON(message.team))
    message.wins !== undefined && (obj.wins = Math.round(message.wins))
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<MapStat>, I>>(object: I): MapStat {
    const message = createBaseMapStat()
    message.map = object.map ?? ""
    message.team = object.team ?? 0
    message.wins = object.wins ?? 0
    return message
  },
}

function createBaseMapResult(): MapResult {
  return { map: "", date: undefined, winner: 0 }
}

export const MapResult = {
  encode(
    message: MapResult,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    if (message.map !== "") {
      writer.uint32(10).string(message.map)
    }
    if (message.date !== undefined) {
      DateMessage.encode(message.date, writer.uint32(18).fork()).ldelim()
    }
    if (message.winner !== 0) {
      writer.uint32(24).int32(message.winner)
    }
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): MapResult {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBaseMapResult()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.map = reader.string()
          break
        case 2:
          message.date = DateMessage.decode(reader, reader.uint32())
          break
        case 3:
          message.winner = reader.int32() as any
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): MapResult {
    return {
      map: isSet(object.map) ? String(object.map) : "",
      date: isSet(object.date) ? DateMessage.fromJSON(object.date) : undefined,
      winner: isSet(object.winner) ? teamFromJSON(object.winner) : 0,
    }
  },

  toJSON(message: MapResult): unknown {
    const obj: any = {}
    message.map !== undefined && (obj.map = message.map)
    message.date !== undefined &&
      (obj.date = message.date ? DateMessage.toJSON(message.date) : undefined)
    message.winner !== undefined && (obj.winner = teamToJSON(message.winner))
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<MapResult>, I>>(
    object: I
  ): MapResult {
    const message = createBaseMapResult()
    message.map = object.map ?? ""
    message.date =
      object.date !== undefined && object.date !== null
        ? DateMessage.fromPartial(object.date)
        : undefined
    message.winner = object.winner ?? 0
    return message
  },
}

function createBaseMapResults(): MapResults {
  return { results: [] }
}

export const MapResults = {
  encode(
    message: MapResults,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    for (const v of message.results) {
      MapResult.encode(v!, writer.uint32(10).fork()).ldelim()
    }
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): MapResults {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBaseMapResults()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.results.push(MapResult.decode(reader, reader.uint32()))
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): MapResults {
    return {
      results: Array.isArray(object?.results)
        ? object.results.map((e: any) => MapResult.fromJSON(e))
        : [],
    }
  },

  toJSON(message: MapResults): unknown {
    const obj: any = {}
    if (message.results) {
      obj.results = message.results.map((e) =>
        e ? MapResult.toJSON(e) : undefined
      )
    } else {
      obj.results = []
    }
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<MapResults>, I>>(
    object: I
  ): MapResults {
    const message = createBaseMapResults()
    message.results = object.results?.map((e) => MapResult.fromPartial(e)) || []
    return message
  },
}

function createBaseMapStats(): MapStats {
  return { mapStats: [], overTime: {} }
}

export const MapStats = {
  encode(
    message: MapStats,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    for (const v of message.mapStats) {
      MapStat.encode(v!, writer.uint32(10).fork()).ldelim()
    }
    Object.entries(message.overTime).forEach(([key, value]) => {
      MapStats_OverTimeEntry.encode(
        { key: key as any, value },
        writer.uint32(18).fork()
      ).ldelim()
    })
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): MapStats {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBaseMapStats()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.mapStats.push(MapStat.decode(reader, reader.uint32()))
          break
        case 2:
          const entry2 = MapStats_OverTimeEntry.decode(reader, reader.uint32())
          if (entry2.value !== undefined) {
            message.overTime[entry2.key] = entry2.value
          }
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): MapStats {
    return {
      mapStats: Array.isArray(object?.mapStats)
        ? object.mapStats.map((e: any) => MapStat.fromJSON(e))
        : [],
      overTime: isObject(object.overTime)
        ? Object.entries(object.overTime).reduce<{ [key: string]: MapResults }>(
            (acc, [key, value]) => {
              acc[key] = MapResults.fromJSON(value)
              return acc
            },
            {}
          )
        : {},
    }
  },

  toJSON(message: MapStats): unknown {
    const obj: any = {}
    if (message.mapStats) {
      obj.mapStats = message.mapStats.map((e) =>
        e ? MapStat.toJSON(e) : undefined
      )
    } else {
      obj.mapStats = []
    }
    obj.overTime = {}
    if (message.overTime) {
      Object.entries(message.overTime).forEach(([k, v]) => {
        obj.overTime[k] = MapResults.toJSON(v)
      })
    }
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<MapStats>, I>>(object: I): MapStats {
    const message = createBaseMapStats()
    message.mapStats = object.mapStats?.map((e) => MapStat.fromPartial(e)) || []
    message.overTime = Object.entries(object.overTime ?? {}).reduce<{
      [key: string]: MapResults
    }>((acc, [key, value]) => {
      if (value !== undefined) {
        acc[key] = MapResults.fromPartial(value)
      }
      return acc
    }, {})
    return message
  },
}

function createBaseMapStats_OverTimeEntry(): MapStats_OverTimeEntry {
  return { key: "", value: undefined }
}

export const MapStats_OverTimeEntry = {
  encode(
    message: MapStats_OverTimeEntry,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    if (message.key !== "") {
      writer.uint32(10).string(message.key)
    }
    if (message.value !== undefined) {
      MapResults.encode(message.value, writer.uint32(18).fork()).ldelim()
    }
    return writer
  },

  decode(
    input: _m0.Reader | Uint8Array,
    length?: number
  ): MapStats_OverTimeEntry {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBaseMapStats_OverTimeEntry()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.key = reader.string()
          break
        case 2:
          message.value = MapResults.decode(reader, reader.uint32())
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): MapStats_OverTimeEntry {
    return {
      key: isSet(object.key) ? String(object.key) : "",
      value: isSet(object.value)
        ? MapResults.fromJSON(object.value)
        : undefined,
    }
  },

  toJSON(message: MapStats_OverTimeEntry): unknown {
    const obj: any = {}
    message.key !== undefined && (obj.key = message.key)
    message.value !== undefined &&
      (obj.value = message.value ? MapResults.toJSON(message.value) : undefined)
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<MapStats_OverTimeEntry>, I>>(
    object: I
  ): MapStats_OverTimeEntry {
    const message = createBaseMapStats_OverTimeEntry()
    message.key = object.key ?? ""
    message.value =
      object.value !== undefined && object.value !== null
        ? MapResults.fromPartial(object.value)
        : undefined
    return message
  },
}

function createBaseSaveResponse(): SaveResponse {
  return { success: false }
}

export const SaveResponse = {
  encode(
    message: SaveResponse,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    if (message.success === true) {
      writer.uint32(8).bool(message.success)
    }
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): SaveResponse {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBaseSaveResponse()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.success = reader.bool()
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): SaveResponse {
    return {
      success: isSet(object.success) ? Boolean(object.success) : false,
    }
  },

  toJSON(message: SaveResponse): unknown {
    const obj: any = {}
    message.success !== undefined && (obj.success = message.success)
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<SaveResponse>, I>>(
    object: I
  ): SaveResponse {
    const message = createBaseSaveResponse()
    message.success = object.success ?? false
    return message
  },
}

function createBaseCosts(): Costs {
  return { player: undefined, buildings: [], units: [], upgrades: [] }
}

export const Costs = {
  encode(message: Costs, writer: _m0.Writer = _m0.Writer.create()): _m0.Writer {
    if (message.player !== undefined) {
      Player.encode(message.player, writer.uint32(18).fork()).ldelim()
    }
    for (const v of message.buildings) {
      Costs_BuiltObject.encode(v!, writer.uint32(26).fork()).ldelim()
    }
    for (const v of message.units) {
      Costs_BuiltObject.encode(v!, writer.uint32(34).fork()).ldelim()
    }
    for (const v of message.upgrades) {
      Costs_BuiltObject.encode(v!, writer.uint32(42).fork()).ldelim()
    }
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): Costs {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBaseCosts()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 2:
          message.player = Player.decode(reader, reader.uint32())
          break
        case 3:
          message.buildings.push(
            Costs_BuiltObject.decode(reader, reader.uint32())
          )
          break
        case 4:
          message.units.push(Costs_BuiltObject.decode(reader, reader.uint32()))
          break
        case 5:
          message.upgrades.push(
            Costs_BuiltObject.decode(reader, reader.uint32())
          )
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): Costs {
    return {
      player: isSet(object.player) ? Player.fromJSON(object.player) : undefined,
      buildings: Array.isArray(object?.buildings)
        ? object.buildings.map((e: any) => Costs_BuiltObject.fromJSON(e))
        : [],
      units: Array.isArray(object?.units)
        ? object.units.map((e: any) => Costs_BuiltObject.fromJSON(e))
        : [],
      upgrades: Array.isArray(object?.upgrades)
        ? object.upgrades.map((e: any) => Costs_BuiltObject.fromJSON(e))
        : [],
    }
  },

  toJSON(message: Costs): unknown {
    const obj: any = {}
    message.player !== undefined &&
      (obj.player = message.player ? Player.toJSON(message.player) : undefined)
    if (message.buildings) {
      obj.buildings = message.buildings.map((e) =>
        e ? Costs_BuiltObject.toJSON(e) : undefined
      )
    } else {
      obj.buildings = []
    }
    if (message.units) {
      obj.units = message.units.map((e) =>
        e ? Costs_BuiltObject.toJSON(e) : undefined
      )
    } else {
      obj.units = []
    }
    if (message.upgrades) {
      obj.upgrades = message.upgrades.map((e) =>
        e ? Costs_BuiltObject.toJSON(e) : undefined
      )
    } else {
      obj.upgrades = []
    }
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<Costs>, I>>(object: I): Costs {
    const message = createBaseCosts()
    message.player =
      object.player !== undefined && object.player !== null
        ? Player.fromPartial(object.player)
        : undefined
    message.buildings =
      object.buildings?.map((e) => Costs_BuiltObject.fromPartial(e)) || []
    message.units =
      object.units?.map((e) => Costs_BuiltObject.fromPartial(e)) || []
    message.upgrades =
      object.upgrades?.map((e) => Costs_BuiltObject.fromPartial(e)) || []
    return message
  },
}

function createBaseCosts_BuiltObject(): Costs_BuiltObject {
  return { name: "", count: 0, totalSpent: 0 }
}

export const Costs_BuiltObject = {
  encode(
    message: Costs_BuiltObject,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    if (message.name !== "") {
      writer.uint32(10).string(message.name)
    }
    if (message.count !== 0) {
      writer.uint32(16).int32(message.count)
    }
    if (message.totalSpent !== 0) {
      writer.uint32(24).int32(message.totalSpent)
    }
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): Costs_BuiltObject {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBaseCosts_BuiltObject()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.name = reader.string()
          break
        case 2:
          message.count = reader.int32()
          break
        case 3:
          message.totalSpent = reader.int32()
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): Costs_BuiltObject {
    return {
      name: isSet(object.name) ? String(object.name) : "",
      count: isSet(object.count) ? Number(object.count) : 0,
      totalSpent: isSet(object.totalSpent) ? Number(object.totalSpent) : 0,
    }
  },

  toJSON(message: Costs_BuiltObject): unknown {
    const obj: any = {}
    message.name !== undefined && (obj.name = message.name)
    message.count !== undefined && (obj.count = Math.round(message.count))
    message.totalSpent !== undefined &&
      (obj.totalSpent = Math.round(message.totalSpent))
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<Costs_BuiltObject>, I>>(
    object: I
  ): Costs_BuiltObject {
    const message = createBaseCosts_BuiltObject()
    message.name = object.name ?? ""
    message.count = object.count ?? 0
    message.totalSpent = object.totalSpent ?? 0
    return message
  },
}

function createBaseAPM(): APM {
  return { playerName: "", actionCount: 0, minutes: 0, apm: 0 }
}

export const APM = {
  encode(message: APM, writer: _m0.Writer = _m0.Writer.create()): _m0.Writer {
    if (message.playerName !== "") {
      writer.uint32(10).string(message.playerName)
    }
    if (message.actionCount !== 0) {
      writer.uint32(16).int64(message.actionCount)
    }
    if (message.minutes !== 0) {
      writer.uint32(25).double(message.minutes)
    }
    if (message.apm !== 0) {
      writer.uint32(33).double(message.apm)
    }
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): APM {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBaseAPM()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.playerName = reader.string()
          break
        case 2:
          message.actionCount = longToNumber(reader.int64() as Long)
          break
        case 3:
          message.minutes = reader.double()
          break
        case 4:
          message.apm = reader.double()
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): APM {
    return {
      playerName: isSet(object.playerName) ? String(object.playerName) : "",
      actionCount: isSet(object.actionCount) ? Number(object.actionCount) : 0,
      minutes: isSet(object.minutes) ? Number(object.minutes) : 0,
      apm: isSet(object.apm) ? Number(object.apm) : 0,
    }
  },

  toJSON(message: APM): unknown {
    const obj: any = {}
    message.playerName !== undefined && (obj.playerName = message.playerName)
    message.actionCount !== undefined &&
      (obj.actionCount = Math.round(message.actionCount))
    message.minutes !== undefined && (obj.minutes = message.minutes)
    message.apm !== undefined && (obj.apm = message.apm)
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<APM>, I>>(object: I): APM {
    const message = createBaseAPM()
    message.playerName = object.playerName ?? ""
    message.actionCount = object.actionCount ?? 0
    message.minutes = object.minutes ?? 0
    message.apm = object.apm ?? 0
    return message
  },
}

function createBaseUpgradeEvent(): UpgradeEvent {
  return { playerName: "", timecode: 0, upgradeName: "", cost: 0, atMinute: 0 }
}

export const UpgradeEvent = {
  encode(
    message: UpgradeEvent,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    if (message.playerName !== "") {
      writer.uint32(10).string(message.playerName)
    }
    if (message.timecode !== 0) {
      writer.uint32(16).int64(message.timecode)
    }
    if (message.upgradeName !== "") {
      writer.uint32(26).string(message.upgradeName)
    }
    if (message.cost !== 0) {
      writer.uint32(32).int64(message.cost)
    }
    if (message.atMinute !== 0) {
      writer.uint32(41).double(message.atMinute)
    }
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): UpgradeEvent {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBaseUpgradeEvent()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.playerName = reader.string()
          break
        case 2:
          message.timecode = longToNumber(reader.int64() as Long)
          break
        case 3:
          message.upgradeName = reader.string()
          break
        case 4:
          message.cost = longToNumber(reader.int64() as Long)
          break
        case 5:
          message.atMinute = reader.double()
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): UpgradeEvent {
    return {
      playerName: isSet(object.playerName) ? String(object.playerName) : "",
      timecode: isSet(object.timecode) ? Number(object.timecode) : 0,
      upgradeName: isSet(object.upgradeName) ? String(object.upgradeName) : "",
      cost: isSet(object.cost) ? Number(object.cost) : 0,
      atMinute: isSet(object.atMinute) ? Number(object.atMinute) : 0,
    }
  },

  toJSON(message: UpgradeEvent): unknown {
    const obj: any = {}
    message.playerName !== undefined && (obj.playerName = message.playerName)
    message.timecode !== undefined &&
      (obj.timecode = Math.round(message.timecode))
    message.upgradeName !== undefined && (obj.upgradeName = message.upgradeName)
    message.cost !== undefined && (obj.cost = Math.round(message.cost))
    message.atMinute !== undefined && (obj.atMinute = message.atMinute)
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<UpgradeEvent>, I>>(
    object: I
  ): UpgradeEvent {
    const message = createBaseUpgradeEvent()
    message.playerName = object.playerName ?? ""
    message.timecode = object.timecode ?? 0
    message.upgradeName = object.upgradeName ?? ""
    message.cost = object.cost ?? 0
    message.atMinute = object.atMinute ?? 0
    return message
  },
}

function createBaseSpent(): Spent {
  return { playerName: "", accCost: 0, atMinute: 0 }
}

export const Spent = {
  encode(message: Spent, writer: _m0.Writer = _m0.Writer.create()): _m0.Writer {
    if (message.playerName !== "") {
      writer.uint32(10).string(message.playerName)
    }
    if (message.accCost !== 0) {
      writer.uint32(32).int64(message.accCost)
    }
    if (message.atMinute !== 0) {
      writer.uint32(41).double(message.atMinute)
    }
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): Spent {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBaseSpent()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.playerName = reader.string()
          break
        case 4:
          message.accCost = longToNumber(reader.int64() as Long)
          break
        case 5:
          message.atMinute = reader.double()
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): Spent {
    return {
      playerName: isSet(object.playerName) ? String(object.playerName) : "",
      accCost: isSet(object.accCost) ? Number(object.accCost) : 0,
      atMinute: isSet(object.atMinute) ? Number(object.atMinute) : 0,
    }
  },

  toJSON(message: Spent): unknown {
    const obj: any = {}
    message.playerName !== undefined && (obj.playerName = message.playerName)
    message.accCost !== undefined && (obj.accCost = Math.round(message.accCost))
    message.atMinute !== undefined && (obj.atMinute = message.atMinute)
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<Spent>, I>>(object: I): Spent {
    const message = createBaseSpent()
    message.playerName = object.playerName ?? ""
    message.accCost = object.accCost ?? 0
    message.atMinute = object.atMinute ?? 0
    return message
  },
}

function createBaseUpgrades(): Upgrades {
  return { upgrades: [] }
}

export const Upgrades = {
  encode(
    message: Upgrades,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    for (const v of message.upgrades) {
      UpgradeEvent.encode(v!, writer.uint32(10).fork()).ldelim()
    }
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): Upgrades {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBaseUpgrades()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.upgrades.push(UpgradeEvent.decode(reader, reader.uint32()))
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): Upgrades {
    return {
      upgrades: Array.isArray(object?.upgrades)
        ? object.upgrades.map((e: any) => UpgradeEvent.fromJSON(e))
        : [],
    }
  },

  toJSON(message: Upgrades): unknown {
    const obj: any = {}
    if (message.upgrades) {
      obj.upgrades = message.upgrades.map((e) =>
        e ? UpgradeEvent.toJSON(e) : undefined
      )
    } else {
      obj.upgrades = []
    }
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<Upgrades>, I>>(object: I): Upgrades {
    const message = createBaseUpgrades()
    message.upgrades =
      object.upgrades?.map((e) => UpgradeEvent.fromPartial(e)) || []
    return message
  },
}

function createBaseSpentOverTime(): SpentOverTime {
  return { buildings: [], units: [], upgrades: [], total: [] }
}

export const SpentOverTime = {
  encode(
    message: SpentOverTime,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    for (const v of message.buildings) {
      Spent.encode(v!, writer.uint32(10).fork()).ldelim()
    }
    for (const v of message.units) {
      Spent.encode(v!, writer.uint32(18).fork()).ldelim()
    }
    for (const v of message.upgrades) {
      Spent.encode(v!, writer.uint32(26).fork()).ldelim()
    }
    for (const v of message.total) {
      Spent.encode(v!, writer.uint32(74).fork()).ldelim()
    }
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): SpentOverTime {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBaseSpentOverTime()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.buildings.push(Spent.decode(reader, reader.uint32()))
          break
        case 2:
          message.units.push(Spent.decode(reader, reader.uint32()))
          break
        case 3:
          message.upgrades.push(Spent.decode(reader, reader.uint32()))
          break
        case 9:
          message.total.push(Spent.decode(reader, reader.uint32()))
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): SpentOverTime {
    return {
      buildings: Array.isArray(object?.buildings)
        ? object.buildings.map((e: any) => Spent.fromJSON(e))
        : [],
      units: Array.isArray(object?.units)
        ? object.units.map((e: any) => Spent.fromJSON(e))
        : [],
      upgrades: Array.isArray(object?.upgrades)
        ? object.upgrades.map((e: any) => Spent.fromJSON(e))
        : [],
      total: Array.isArray(object?.total)
        ? object.total.map((e: any) => Spent.fromJSON(e))
        : [],
    }
  },

  toJSON(message: SpentOverTime): unknown {
    const obj: any = {}
    if (message.buildings) {
      obj.buildings = message.buildings.map((e) =>
        e ? Spent.toJSON(e) : undefined
      )
    } else {
      obj.buildings = []
    }
    if (message.units) {
      obj.units = message.units.map((e) => (e ? Spent.toJSON(e) : undefined))
    } else {
      obj.units = []
    }
    if (message.upgrades) {
      obj.upgrades = message.upgrades.map((e) =>
        e ? Spent.toJSON(e) : undefined
      )
    } else {
      obj.upgrades = []
    }
    if (message.total) {
      obj.total = message.total.map((e) => (e ? Spent.toJSON(e) : undefined))
    } else {
      obj.total = []
    }
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<SpentOverTime>, I>>(
    object: I
  ): SpentOverTime {
    const message = createBaseSpentOverTime()
    message.buildings = object.buildings?.map((e) => Spent.fromPartial(e)) || []
    message.units = object.units?.map((e) => Spent.fromPartial(e)) || []
    message.upgrades = object.upgrades?.map((e) => Spent.fromPartial(e)) || []
    message.total = object.total?.map((e) => Spent.fromPartial(e)) || []
    return message
  },
}

function createBaseMatchDetails(): MatchDetails {
  return {
    matchId: 0,
    costs: [],
    apms: [],
    upgradeEvents: {},
    spent: undefined,
  }
}

export const MatchDetails = {
  encode(
    message: MatchDetails,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    if (message.matchId !== 0) {
      writer.uint32(8).int64(message.matchId)
    }
    for (const v of message.costs) {
      Costs.encode(v!, writer.uint32(18).fork()).ldelim()
    }
    for (const v of message.apms) {
      APM.encode(v!, writer.uint32(26).fork()).ldelim()
    }
    Object.entries(message.upgradeEvents).forEach(([key, value]) => {
      MatchDetails_UpgradeEventsEntry.encode(
        { key: key as any, value },
        writer.uint32(34).fork()
      ).ldelim()
    })
    if (message.spent !== undefined) {
      SpentOverTime.encode(message.spent, writer.uint32(42).fork()).ldelim()
    }
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): MatchDetails {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBaseMatchDetails()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.matchId = longToNumber(reader.int64() as Long)
          break
        case 2:
          message.costs.push(Costs.decode(reader, reader.uint32()))
          break
        case 3:
          message.apms.push(APM.decode(reader, reader.uint32()))
          break
        case 4:
          const entry4 = MatchDetails_UpgradeEventsEntry.decode(
            reader,
            reader.uint32()
          )
          if (entry4.value !== undefined) {
            message.upgradeEvents[entry4.key] = entry4.value
          }
          break
        case 5:
          message.spent = SpentOverTime.decode(reader, reader.uint32())
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): MatchDetails {
    return {
      matchId: isSet(object.matchId) ? Number(object.matchId) : 0,
      costs: Array.isArray(object?.costs)
        ? object.costs.map((e: any) => Costs.fromJSON(e))
        : [],
      apms: Array.isArray(object?.apms)
        ? object.apms.map((e: any) => APM.fromJSON(e))
        : [],
      upgradeEvents: isObject(object.upgradeEvents)
        ? Object.entries(object.upgradeEvents).reduce<{
            [key: string]: Upgrades
          }>((acc, [key, value]) => {
            acc[key] = Upgrades.fromJSON(value)
            return acc
          }, {})
        : {},
      spent: isSet(object.spent)
        ? SpentOverTime.fromJSON(object.spent)
        : undefined,
    }
  },

  toJSON(message: MatchDetails): unknown {
    const obj: any = {}
    message.matchId !== undefined && (obj.matchId = Math.round(message.matchId))
    if (message.costs) {
      obj.costs = message.costs.map((e) => (e ? Costs.toJSON(e) : undefined))
    } else {
      obj.costs = []
    }
    if (message.apms) {
      obj.apms = message.apms.map((e) => (e ? APM.toJSON(e) : undefined))
    } else {
      obj.apms = []
    }
    obj.upgradeEvents = {}
    if (message.upgradeEvents) {
      Object.entries(message.upgradeEvents).forEach(([k, v]) => {
        obj.upgradeEvents[k] = Upgrades.toJSON(v)
      })
    }
    message.spent !== undefined &&
      (obj.spent = message.spent
        ? SpentOverTime.toJSON(message.spent)
        : undefined)
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<MatchDetails>, I>>(
    object: I
  ): MatchDetails {
    const message = createBaseMatchDetails()
    message.matchId = object.matchId ?? 0
    message.costs = object.costs?.map((e) => Costs.fromPartial(e)) || []
    message.apms = object.apms?.map((e) => APM.fromPartial(e)) || []
    message.upgradeEvents = Object.entries(object.upgradeEvents ?? {}).reduce<{
      [key: string]: Upgrades
    }>((acc, [key, value]) => {
      if (value !== undefined) {
        acc[key] = Upgrades.fromPartial(value)
      }
      return acc
    }, {})
    message.spent =
      object.spent !== undefined && object.spent !== null
        ? SpentOverTime.fromPartial(object.spent)
        : undefined
    return message
  },
}

function createBaseMatchDetails_UpgradeEventsEntry(): MatchDetails_UpgradeEventsEntry {
  return { key: "", value: undefined }
}

export const MatchDetails_UpgradeEventsEntry = {
  encode(
    message: MatchDetails_UpgradeEventsEntry,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    if (message.key !== "") {
      writer.uint32(10).string(message.key)
    }
    if (message.value !== undefined) {
      Upgrades.encode(message.value, writer.uint32(18).fork()).ldelim()
    }
    return writer
  },

  decode(
    input: _m0.Reader | Uint8Array,
    length?: number
  ): MatchDetails_UpgradeEventsEntry {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBaseMatchDetails_UpgradeEventsEntry()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.key = reader.string()
          break
        case 2:
          message.value = Upgrades.decode(reader, reader.uint32())
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): MatchDetails_UpgradeEventsEntry {
    return {
      key: isSet(object.key) ? String(object.key) : "",
      value: isSet(object.value) ? Upgrades.fromJSON(object.value) : undefined,
    }
  },

  toJSON(message: MatchDetails_UpgradeEventsEntry): unknown {
    const obj: any = {}
    message.key !== undefined && (obj.key = message.key)
    message.value !== undefined &&
      (obj.value = message.value ? Upgrades.toJSON(message.value) : undefined)
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<MatchDetails_UpgradeEventsEntry>, I>>(
    object: I
  ): MatchDetails_UpgradeEventsEntry {
    const message = createBaseMatchDetails_UpgradeEventsEntry()
    message.key = object.key ?? ""
    message.value =
      object.value !== undefined && object.value !== null
        ? Upgrades.fromPartial(object.value)
        : undefined
    return message
  },
}

function createBasePairWinLoss(): PairWinLoss {
  return { general1: 0, general2: 0, winloss: undefined }
}

export const PairWinLoss = {
  encode(
    message: PairWinLoss,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    if (message.general1 !== 0) {
      writer.uint32(8).int32(message.general1)
    }
    if (message.general2 !== 0) {
      writer.uint32(16).int32(message.general2)
    }
    if (message.winloss !== undefined) {
      WinLoss.encode(message.winloss, writer.uint32(26).fork()).ldelim()
    }
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): PairWinLoss {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBasePairWinLoss()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.general1 = reader.int32() as any
          break
        case 2:
          message.general2 = reader.int32() as any
          break
        case 3:
          message.winloss = WinLoss.decode(reader, reader.uint32())
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): PairWinLoss {
    return {
      general1: isSet(object.general1) ? generalFromJSON(object.general1) : 0,
      general2: isSet(object.general2) ? generalFromJSON(object.general2) : 0,
      winloss: isSet(object.winloss)
        ? WinLoss.fromJSON(object.winloss)
        : undefined,
    }
  },

  toJSON(message: PairWinLoss): unknown {
    const obj: any = {}
    message.general1 !== undefined &&
      (obj.general1 = generalToJSON(message.general1))
    message.general2 !== undefined &&
      (obj.general2 = generalToJSON(message.general2))
    message.winloss !== undefined &&
      (obj.winloss = message.winloss
        ? WinLoss.toJSON(message.winloss)
        : undefined)
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<PairWinLoss>, I>>(
    object: I
  ): PairWinLoss {
    const message = createBasePairWinLoss()
    message.general1 = object.general1 ?? 0
    message.general2 = object.general2 ?? 0
    message.winloss =
      object.winloss !== undefined && object.winloss !== null
        ? WinLoss.fromPartial(object.winloss)
        : undefined
    return message
  },
}

function createBasePairFactionWinLoss(): PairFactionWinLoss {
  return { faction1: 0, faction2: 0, winloss: undefined }
}

export const PairFactionWinLoss = {
  encode(
    message: PairFactionWinLoss,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    if (message.faction1 !== 0) {
      writer.uint32(8).int32(message.faction1)
    }
    if (message.faction2 !== 0) {
      writer.uint32(16).int32(message.faction2)
    }
    if (message.winloss !== undefined) {
      WinLoss.encode(message.winloss, writer.uint32(26).fork()).ldelim()
    }
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): PairFactionWinLoss {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBasePairFactionWinLoss()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.faction1 = reader.int32() as any
          break
        case 2:
          message.faction2 = reader.int32() as any
          break
        case 3:
          message.winloss = WinLoss.decode(reader, reader.uint32())
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): PairFactionWinLoss {
    return {
      faction1: isSet(object.faction1) ? factionFromJSON(object.faction1) : 0,
      faction2: isSet(object.faction2) ? factionFromJSON(object.faction2) : 0,
      winloss: isSet(object.winloss)
        ? WinLoss.fromJSON(object.winloss)
        : undefined,
    }
  },

  toJSON(message: PairFactionWinLoss): unknown {
    const obj: any = {}
    message.faction1 !== undefined &&
      (obj.faction1 = factionToJSON(message.faction1))
    message.faction2 !== undefined &&
      (obj.faction2 = factionToJSON(message.faction2))
    message.winloss !== undefined &&
      (obj.winloss = message.winloss
        ? WinLoss.toJSON(message.winloss)
        : undefined)
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<PairFactionWinLoss>, I>>(
    object: I
  ): PairFactionWinLoss {
    const message = createBasePairFactionWinLoss()
    message.faction1 = object.faction1 ?? 0
    message.faction2 = object.faction2 ?? 0
    message.winloss =
      object.winloss !== undefined && object.winloss !== null
        ? WinLoss.fromPartial(object.winloss)
        : undefined
    return message
  },
}

function createBasePairsWinLosses(): PairsWinLosses {
  return { pairwl: [] }
}

export const PairsWinLosses = {
  encode(
    message: PairsWinLosses,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    for (const v of message.pairwl) {
      PairWinLoss.encode(v!, writer.uint32(10).fork()).ldelim()
    }
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): PairsWinLosses {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBasePairsWinLosses()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.pairwl.push(PairWinLoss.decode(reader, reader.uint32()))
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): PairsWinLosses {
    return {
      pairwl: Array.isArray(object?.pairwl)
        ? object.pairwl.map((e: any) => PairWinLoss.fromJSON(e))
        : [],
    }
  },

  toJSON(message: PairsWinLosses): unknown {
    const obj: any = {}
    if (message.pairwl) {
      obj.pairwl = message.pairwl.map((e) =>
        e ? PairWinLoss.toJSON(e) : undefined
      )
    } else {
      obj.pairwl = []
    }
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<PairsWinLosses>, I>>(
    object: I
  ): PairsWinLosses {
    const message = createBasePairsWinLosses()
    message.pairwl = object.pairwl?.map((e) => PairWinLoss.fromPartial(e)) || []
    return message
  },
}

function createBasePairFactionWinLosses(): PairFactionWinLosses {
  return { pairwl: [] }
}

export const PairFactionWinLosses = {
  encode(
    message: PairFactionWinLosses,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    for (const v of message.pairwl) {
      PairFactionWinLoss.encode(v!, writer.uint32(10).fork()).ldelim()
    }
    return writer
  },

  decode(
    input: _m0.Reader | Uint8Array,
    length?: number
  ): PairFactionWinLosses {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBasePairFactionWinLosses()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.pairwl.push(
            PairFactionWinLoss.decode(reader, reader.uint32())
          )
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): PairFactionWinLosses {
    return {
      pairwl: Array.isArray(object?.pairwl)
        ? object.pairwl.map((e: any) => PairFactionWinLoss.fromJSON(e))
        : [],
    }
  },

  toJSON(message: PairFactionWinLosses): unknown {
    const obj: any = {}
    if (message.pairwl) {
      obj.pairwl = message.pairwl.map((e) =>
        e ? PairFactionWinLoss.toJSON(e) : undefined
      )
    } else {
      obj.pairwl = []
    }
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<PairFactionWinLosses>, I>>(
    object: I
  ): PairFactionWinLosses {
    const message = createBasePairFactionWinLosses()
    message.pairwl =
      object.pairwl?.map((e) => PairFactionWinLoss.fromPartial(e)) || []
    return message
  },
}

function createBaseTeamPairs(): TeamPairs {
  return { teamPairs: {}, factionPairs: {} }
}

export const TeamPairs = {
  encode(
    message: TeamPairs,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    Object.entries(message.teamPairs).forEach(([key, value]) => {
      TeamPairs_TeamPairsEntry.encode(
        { key: key as any, value },
        writer.uint32(10).fork()
      ).ldelim()
    })
    Object.entries(message.factionPairs).forEach(([key, value]) => {
      TeamPairs_FactionPairsEntry.encode(
        { key: key as any, value },
        writer.uint32(18).fork()
      ).ldelim()
    })
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): TeamPairs {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBaseTeamPairs()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          const entry1 = TeamPairs_TeamPairsEntry.decode(
            reader,
            reader.uint32()
          )
          if (entry1.value !== undefined) {
            message.teamPairs[entry1.key] = entry1.value
          }
          break
        case 2:
          const entry2 = TeamPairs_FactionPairsEntry.decode(
            reader,
            reader.uint32()
          )
          if (entry2.value !== undefined) {
            message.factionPairs[entry2.key] = entry2.value
          }
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): TeamPairs {
    return {
      teamPairs: isObject(object.teamPairs)
        ? Object.entries(object.teamPairs).reduce<{
            [key: string]: PairsWinLosses
          }>((acc, [key, value]) => {
            acc[key] = PairsWinLosses.fromJSON(value)
            return acc
          }, {})
        : {},
      factionPairs: isObject(object.factionPairs)
        ? Object.entries(object.factionPairs).reduce<{
            [key: string]: PairFactionWinLosses
          }>((acc, [key, value]) => {
            acc[key] = PairFactionWinLosses.fromJSON(value)
            return acc
          }, {})
        : {},
    }
  },

  toJSON(message: TeamPairs): unknown {
    const obj: any = {}
    obj.teamPairs = {}
    if (message.teamPairs) {
      Object.entries(message.teamPairs).forEach(([k, v]) => {
        obj.teamPairs[k] = PairsWinLosses.toJSON(v)
      })
    }
    obj.factionPairs = {}
    if (message.factionPairs) {
      Object.entries(message.factionPairs).forEach(([k, v]) => {
        obj.factionPairs[k] = PairFactionWinLosses.toJSON(v)
      })
    }
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<TeamPairs>, I>>(
    object: I
  ): TeamPairs {
    const message = createBaseTeamPairs()
    message.teamPairs = Object.entries(object.teamPairs ?? {}).reduce<{
      [key: string]: PairsWinLosses
    }>((acc, [key, value]) => {
      if (value !== undefined) {
        acc[key] = PairsWinLosses.fromPartial(value)
      }
      return acc
    }, {})
    message.factionPairs = Object.entries(object.factionPairs ?? {}).reduce<{
      [key: string]: PairFactionWinLosses
    }>((acc, [key, value]) => {
      if (value !== undefined) {
        acc[key] = PairFactionWinLosses.fromPartial(value)
      }
      return acc
    }, {})
    return message
  },
}

function createBaseTeamPairs_TeamPairsEntry(): TeamPairs_TeamPairsEntry {
  return { key: "", value: undefined }
}

export const TeamPairs_TeamPairsEntry = {
  encode(
    message: TeamPairs_TeamPairsEntry,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    if (message.key !== "") {
      writer.uint32(10).string(message.key)
    }
    if (message.value !== undefined) {
      PairsWinLosses.encode(message.value, writer.uint32(18).fork()).ldelim()
    }
    return writer
  },

  decode(
    input: _m0.Reader | Uint8Array,
    length?: number
  ): TeamPairs_TeamPairsEntry {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBaseTeamPairs_TeamPairsEntry()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.key = reader.string()
          break
        case 2:
          message.value = PairsWinLosses.decode(reader, reader.uint32())
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): TeamPairs_TeamPairsEntry {
    return {
      key: isSet(object.key) ? String(object.key) : "",
      value: isSet(object.value)
        ? PairsWinLosses.fromJSON(object.value)
        : undefined,
    }
  },

  toJSON(message: TeamPairs_TeamPairsEntry): unknown {
    const obj: any = {}
    message.key !== undefined && (obj.key = message.key)
    message.value !== undefined &&
      (obj.value = message.value
        ? PairsWinLosses.toJSON(message.value)
        : undefined)
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<TeamPairs_TeamPairsEntry>, I>>(
    object: I
  ): TeamPairs_TeamPairsEntry {
    const message = createBaseTeamPairs_TeamPairsEntry()
    message.key = object.key ?? ""
    message.value =
      object.value !== undefined && object.value !== null
        ? PairsWinLosses.fromPartial(object.value)
        : undefined
    return message
  },
}

function createBaseTeamPairs_FactionPairsEntry(): TeamPairs_FactionPairsEntry {
  return { key: "", value: undefined }
}

export const TeamPairs_FactionPairsEntry = {
  encode(
    message: TeamPairs_FactionPairsEntry,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    if (message.key !== "") {
      writer.uint32(10).string(message.key)
    }
    if (message.value !== undefined) {
      PairFactionWinLosses.encode(
        message.value,
        writer.uint32(18).fork()
      ).ldelim()
    }
    return writer
  },

  decode(
    input: _m0.Reader | Uint8Array,
    length?: number
  ): TeamPairs_FactionPairsEntry {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBaseTeamPairs_FactionPairsEntry()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.key = reader.string()
          break
        case 2:
          message.value = PairFactionWinLosses.decode(reader, reader.uint32())
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): TeamPairs_FactionPairsEntry {
    return {
      key: isSet(object.key) ? String(object.key) : "",
      value: isSet(object.value)
        ? PairFactionWinLosses.fromJSON(object.value)
        : undefined,
    }
  },

  toJSON(message: TeamPairs_FactionPairsEntry): unknown {
    const obj: any = {}
    message.key !== undefined && (obj.key = message.key)
    message.value !== undefined &&
      (obj.value = message.value
        ? PairFactionWinLosses.toJSON(message.value)
        : undefined)
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<TeamPairs_FactionPairsEntry>, I>>(
    object: I
  ): TeamPairs_FactionPairsEntry {
    const message = createBaseTeamPairs_FactionPairsEntry()
    message.key = object.key ?? ""
    message.value =
      object.value !== undefined && object.value !== null
        ? PairFactionWinLosses.fromPartial(object.value)
        : undefined
    return message
  },
}

function createBaseWrapped(): Wrapped {
  return {
    gamesPlayed: 0,
    hoursPlayed: 0,
    mostPlayed: 0,
    mostPlayedWinrate: 0,
    mostBuilt: "",
    mostBuiltSpent: 0,
    mostBuiltCount: 0,
    mostBuiltMore: 0,
    bestGeneral: 0,
    bestWinrate: 0,
    bestAverage: 0,
  }
}

export const Wrapped = {
  encode(
    message: Wrapped,
    writer: _m0.Writer = _m0.Writer.create()
  ): _m0.Writer {
    if (message.gamesPlayed !== 0) {
      writer.uint32(8).int32(message.gamesPlayed)
    }
    if (message.hoursPlayed !== 0) {
      writer.uint32(17).double(message.hoursPlayed)
    }
    if (message.mostPlayed !== 0) {
      writer.uint32(24).int32(message.mostPlayed)
    }
    if (message.mostPlayedWinrate !== 0) {
      writer.uint32(33).double(message.mostPlayedWinrate)
    }
    if (message.mostBuilt !== "") {
      writer.uint32(42).string(message.mostBuilt)
    }
    if (message.mostBuiltSpent !== 0) {
      writer.uint32(49).double(message.mostBuiltSpent)
    }
    if (message.mostBuiltCount !== 0) {
      writer.uint32(56).int32(message.mostBuiltCount)
    }
    if (message.mostBuiltMore !== 0) {
      writer.uint32(64).int32(message.mostBuiltMore)
    }
    if (message.bestGeneral !== 0) {
      writer.uint32(72).int32(message.bestGeneral)
    }
    if (message.bestWinrate !== 0) {
      writer.uint32(81).double(message.bestWinrate)
    }
    if (message.bestAverage !== 0) {
      writer.uint32(89).double(message.bestAverage)
    }
    return writer
  },

  decode(input: _m0.Reader | Uint8Array, length?: number): Wrapped {
    const reader = input instanceof _m0.Reader ? input : new _m0.Reader(input)
    let end = length === undefined ? reader.len : reader.pos + length
    const message = createBaseWrapped()
    while (reader.pos < end) {
      const tag = reader.uint32()
      switch (tag >>> 3) {
        case 1:
          message.gamesPlayed = reader.int32()
          break
        case 2:
          message.hoursPlayed = reader.double()
          break
        case 3:
          message.mostPlayed = reader.int32() as any
          break
        case 4:
          message.mostPlayedWinrate = reader.double()
          break
        case 5:
          message.mostBuilt = reader.string()
          break
        case 6:
          message.mostBuiltSpent = reader.double()
          break
        case 7:
          message.mostBuiltCount = reader.int32()
          break
        case 8:
          message.mostBuiltMore = reader.int32()
          break
        case 9:
          message.bestGeneral = reader.int32() as any
          break
        case 10:
          message.bestWinrate = reader.double()
          break
        case 11:
          message.bestAverage = reader.double()
          break
        default:
          reader.skipType(tag & 7)
          break
      }
    }
    return message
  },

  fromJSON(object: any): Wrapped {
    return {
      gamesPlayed: isSet(object.gamesPlayed) ? Number(object.gamesPlayed) : 0,
      hoursPlayed: isSet(object.hoursPlayed) ? Number(object.hoursPlayed) : 0,
      mostPlayed: isSet(object.mostPlayed)
        ? generalFromJSON(object.mostPlayed)
        : 0,
      mostPlayedWinrate: isSet(object.mostPlayedWinrate)
        ? Number(object.mostPlayedWinrate)
        : 0,
      mostBuilt: isSet(object.mostBuilt) ? String(object.mostBuilt) : "",
      mostBuiltSpent: isSet(object.mostBuiltSpent)
        ? Number(object.mostBuiltSpent)
        : 0,
      mostBuiltCount: isSet(object.mostBuiltCount)
        ? Number(object.mostBuiltCount)
        : 0,
      mostBuiltMore: isSet(object.mostBuiltMore)
        ? Number(object.mostBuiltMore)
        : 0,
      bestGeneral: isSet(object.bestGeneral)
        ? generalFromJSON(object.bestGeneral)
        : 0,
      bestWinrate: isSet(object.bestWinrate) ? Number(object.bestWinrate) : 0,
      bestAverage: isSet(object.bestAverage) ? Number(object.bestAverage) : 0,
    }
  },

  toJSON(message: Wrapped): unknown {
    const obj: any = {}
    message.gamesPlayed !== undefined &&
      (obj.gamesPlayed = Math.round(message.gamesPlayed))
    message.hoursPlayed !== undefined && (obj.hoursPlayed = message.hoursPlayed)
    message.mostPlayed !== undefined &&
      (obj.mostPlayed = generalToJSON(message.mostPlayed))
    message.mostPlayedWinrate !== undefined &&
      (obj.mostPlayedWinrate = message.mostPlayedWinrate)
    message.mostBuilt !== undefined && (obj.mostBuilt = message.mostBuilt)
    message.mostBuiltSpent !== undefined &&
      (obj.mostBuiltSpent = message.mostBuiltSpent)
    message.mostBuiltCount !== undefined &&
      (obj.mostBuiltCount = Math.round(message.mostBuiltCount))
    message.mostBuiltMore !== undefined &&
      (obj.mostBuiltMore = Math.round(message.mostBuiltMore))
    message.bestGeneral !== undefined &&
      (obj.bestGeneral = generalToJSON(message.bestGeneral))
    message.bestWinrate !== undefined && (obj.bestWinrate = message.bestWinrate)
    message.bestAverage !== undefined && (obj.bestAverage = message.bestAverage)
    return obj
  },

  fromPartial<I extends Exact<DeepPartial<Wrapped>, I>>(object: I): Wrapped {
    const message = createBaseWrapped()
    message.gamesPlayed = object.gamesPlayed ?? 0
    message.hoursPlayed = object.hoursPlayed ?? 0
    message.mostPlayed = object.mostPlayed ?? 0
    message.mostPlayedWinrate = object.mostPlayedWinrate ?? 0
    message.mostBuilt = object.mostBuilt ?? ""
    message.mostBuiltSpent = object.mostBuiltSpent ?? 0
    message.mostBuiltCount = object.mostBuiltCount ?? 0
    message.mostBuiltMore = object.mostBuiltMore ?? 0
    message.bestGeneral = object.bestGeneral ?? 0
    message.bestWinrate = object.bestWinrate ?? 0
    message.bestAverage = object.bestAverage ?? 0
    return message
  },
}

declare var self: any | undefined
declare var window: any | undefined
declare var global: any | undefined
var globalThis: any = (() => {
  if (typeof globalThis !== "undefined") return globalThis
  if (typeof self !== "undefined") return self
  if (typeof window !== "undefined") return window
  if (typeof global !== "undefined") return global
  throw "Unable to locate global object"
})()

type Builtin =
  | Date
  | Function
  | Uint8Array
  | string
  | number
  | boolean
  | undefined

export type DeepPartial<T> = T extends Builtin
  ? T
  : T extends Array<infer U>
  ? Array<DeepPartial<U>>
  : T extends ReadonlyArray<infer U>
  ? ReadonlyArray<DeepPartial<U>>
  : T extends {}
  ? { [K in keyof T]?: DeepPartial<T[K]> }
  : Partial<T>

type KeysOfUnion<T> = T extends T ? keyof T : never
export type Exact<P, I extends P> = P extends Builtin
  ? P
  : P & { [K in keyof P]: Exact<P[K], I[K]> } & {
      [K in Exclude<keyof I, KeysOfUnion<P>>]: never
    }

function toTimestamp(date: Date): Timestamp {
  const seconds = date.getTime() / 1_000
  const nanos = (date.getTime() % 1_000) * 1_000_000
  return { seconds, nanos }
}

function fromTimestamp(t: Timestamp): Date {
  let millis = t.seconds * 1_000
  millis += t.nanos / 1_000_000
  return new Date(millis)
}

function fromJsonTimestamp(o: any): Date {
  if (o instanceof Date) {
    return o
  } else if (typeof o === "string") {
    return new Date(o)
  } else {
    return fromTimestamp(Timestamp.fromJSON(o))
  }
}

function longToNumber(long: Long): number {
  if (long.gt(Number.MAX_SAFE_INTEGER)) {
    throw new globalThis.Error("Value is larger than Number.MAX_SAFE_INTEGER")
  }
  return long.toNumber()
}

if (_m0.util.Long !== Long) {
  _m0.util.Long = Long as any
  _m0.configure()
}

function isObject(value: any): boolean {
  return typeof value === "object" && value !== null
}

function isSet(value: any): boolean {
  return value !== null && value !== undefined
}
