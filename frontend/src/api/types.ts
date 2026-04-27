export type ResultType = "REG" | "OT" | "SO";
export type Position = "LW" | "C" | "RW" | "LD" | "RD";

export interface TeamSummary { id: number; name: string; abbreviation: string; }
export interface League {
  season_id: number; seed: number; user_team_id: number | null;
  current_matchday: number; status: "active" | "complete";
  teams: TeamSummary[];
}
export interface Skater {
  id: number; name: string; age: number; position: Position;
  skating: number; shooting: number; passing: number; defense: number; physical: number;
}
export interface Goalie {
  id: number; name: string; age: number;
  reflexes: number; positioning: number; rebound_control: number; puck_handling: number; mental: number;
}
export interface Roster { team: TeamSummary; skaters: Skater[]; goalies: Goalie[]; }
export interface LineupSlots {
  line1_lw_id: number; line1_c_id: number; line1_rw_id: number;
  line2_lw_id: number; line2_c_id: number; line2_rw_id: number;
  line3_lw_id: number; line3_c_id: number; line3_rw_id: number;
  line4_lw_id: number; line4_c_id: number; line4_rw_id: number;
  pair1_ld_id: number; pair1_rd_id: number;
  pair2_ld_id: number; pair2_rd_id: number;
  pair3_ld_id: number; pair3_rd_id: number;
  starting_goalie_id: number; backup_goalie_id: number;
}
export interface Lineup extends LineupSlots { team_id: number; }
export interface GameSummary {
  id: number; matchday: number; home_team_id: number; away_team_id: number;
  status: "scheduled" | "simulated";
  home_score: number | null; away_score: number | null; result_type: ResultType | null;
}
export interface Schedule { games: GameSummary[]; }
export interface StandingRow {
  team_id: number; games_played: number; wins: number; losses: number; ot_losses: number;
  points: number; goals_for: number; goals_against: number;
}
export interface Standings { rows: StandingRow[]; }
export interface GameEvent {
  tick: number; kind: "shot" | "save" | "goal"; team_id: number;
  primary_skater_id: number | null; assist1_id: number | null; assist2_id: number | null;
  goalie_id: number | null;
}
export interface SkaterStat { skater_id: number; goals: number; assists: number; shots: number; }
export interface GoalieStat { goalie_id: number; shots_against: number; saves: number; goals_against: number; }
export interface GameDetail {
  id: number; matchday: number; home_team_id: number; away_team_id: number;
  status: "scheduled" | "simulated";
  home_score: number | null; away_score: number | null;
  home_shots: number | null; away_shots: number | null;
  result_type: ResultType | null;
  events: GameEvent[]; skater_stats: SkaterStat[]; goalie_stats: GoalieStat[];
}
export interface AdvanceResponse {
  advanced_game_ids: number[]; current_matchday: number; season_status: "active" | "complete";
}
export interface SeasonStatus { current_matchday: number; status: "active" | "complete"; }
export interface ApiError { error_code: string; message: string; }
