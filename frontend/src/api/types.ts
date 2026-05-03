export type ResultType = "REG" | "OT" | "SO";
export type Position = "LW" | "C" | "RW" | "LD" | "RD";

export interface TeamSummary { id: number; name: string; abbreviation: string; }
export interface League {
  season_id: number; seed: number; user_team_id: number | null;
  current_matchday: number; status: "active" | "complete";
  teams: TeamSummary[];
}
export interface Skater {
  id: number; name: string; age: number; position: Position; potential: number;
  skating: number; shooting: number; passing: number; defense: number; physical: number;
}
export interface Goalie {
  id: number; name: string; age: number; potential: number;
  reflexes: number; positioning: number; rebound_control: number; puck_handling: number; mental: number;
}
export interface Roster { team: TeamSummary; skaters: Skater[]; goalies: Goalie[]; }
export interface LineupSlots {
  line1_lw_id: number | null; line1_c_id: number | null; line1_rw_id: number | null;
  line2_lw_id: number | null; line2_c_id: number | null; line2_rw_id: number | null;
  line3_lw_id: number | null; line3_c_id: number | null; line3_rw_id: number | null;
  line4_lw_id: number | null; line4_c_id: number | null; line4_rw_id: number | null;
  pair1_ld_id: number | null; pair1_rd_id: number | null;
  pair2_ld_id: number | null; pair2_rd_id: number | null;
  pair3_ld_id: number | null; pair3_rd_id: number | null;
  starting_goalie_id: number | null; backup_goalie_id: number | null;
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
  tick: number; period: number;
  kind: "shot" | "save" | "goal" | "penalty";
  strength: "EV" | "PP" | "SH" | null;
  team_id: number;
  primary_skater_id: number | null; primary_skater_name: string | null;
  assist1_id: number | null; assist1_name: string | null;
  assist2_id: number | null; assist2_name: string | null;
  goalie_id: number | null; goalie_name: string | null;
  penalty_duration_ticks: number | null;
  shot_quality: "LOW" | "MEDIUM" | "HIGH" | null;
}
export interface SkaterStat { skater_id: number; skater_name: string; goals: number; assists: number; shots: number; }
export interface GoalieStat { goalie_id: number; goalie_name: string; shots_against: number; saves: number; goals_against: number; }
export interface GameDetail {
  id: number; matchday: number; home_team_id: number; away_team_id: number;
  status: "scheduled" | "simulated";
  home_score: number | null; away_score: number | null;
  home_shots: number | null; away_shots: number | null;
  result_type: ResultType | null;
  events: GameEvent[]; skater_stats: SkaterStat[]; goalie_stats: GoalieStat[];
  home_goals_by_period: number[];
  away_goals_by_period: number[];
  home_shots_by_period: number[];
  away_shots_by_period: number[];
}
export interface AdvanceResponse {
  advanced_game_ids: number[]; current_matchday: number; season_status: "active" | "complete";
}
export interface SeasonStatus { current_matchday: number; status: "active" | "complete"; }
export interface SeasonStats {
  games_played: number;
  avg_total_goals_per_game: number;
  avg_total_shots_per_game: number;
  avg_home_goals: number;
  avg_away_goals: number;
  avg_home_shots: number;
  avg_away_shots: number;
  league_save_percentage: number;
  league_shooting_percentage: number;
  home_win_pct: number;
  overtime_pct: number;
  shootout_pct: number;
  penalties_per_game: number;
  pp_goals_per_game: number;
  sh_goals_per_game: number;
  top_scorer_name: string | null;
  top_scorer_points: number;
  top_scorer_goals: number;
  top_scorer_assists: number;
  top_goalie_name: string | null;
  top_goalie_save_pct: number;
  top_goalie_shots_against: number;
}
export interface SkaterStatRow {
  skater_id: number; name: string; team_id: number; position: Position;
  games_played: number; goals: number; assists: number; points: number;
  shots: number; shooting_pct: number;
}
export interface SkatersStats { rows: SkaterStatRow[]; }

export interface GoalieStatRow {
  goalie_id: number; name: string; team_id: number;
  games_played: number; shots_against: number; saves: number; goals_against: number;
  save_pct: number; gaa: number;
}
export interface GoaliesStats { rows: GoalieStatRow[]; }

export interface TeamStatRow {
  team_id: number;
  games_played: number; wins: number; losses: number; ot_losses: number; points: number;
  goals_for: number; goals_against: number; diff: number;
  goals_per_game: number; shots_per_game: number;
  save_pct: number; shooting_pct: number;
  pp_pct: number; pk_pct: number;
}
export interface TeamsStats { rows: TeamStatRow[]; }

export interface SkaterTotals {
  games_played: number; goals: number; assists: number; points: number; shots: number; shooting_pct: number;
}
export interface SkaterGameLogRow {
  game_id: number; matchday: number; opponent_team_id: number; is_home: boolean;
  goals: number; assists: number; points: number; shots: number;
}
export interface SkaterDetail {
  id: number; name: string; age: number; position: Position; team_id: number;
  potential: number; development_type: string;
  attributes: { skating: number; shooting: number; passing: number; defense: number; physical: number };
  totals: SkaterTotals;
  game_log: SkaterGameLogRow[];
}

export interface GoalieTotals {
  games_played: number; shots_against: number; saves: number; goals_against: number; save_pct: number; gaa: number;
}
export interface GoalieGameLogRow {
  game_id: number; matchday: number; opponent_team_id: number; is_home: boolean;
  shots_against: number; saves: number; goals_against: number; save_pct: number;
}
export interface GoalieDetail {
  id: number; name: string; age: number; team_id: number;
  potential: number; development_type: string;
  attributes: { reflexes: number; positioning: number; rebound_control: number; puck_handling: number; mental: number };
  totals: GoalieTotals;
  game_log: GoalieGameLogRow[];
}

export interface DevelopmentEventOut {
  attribute: string; old_value: number; new_value: number; delta: number; reason: string;
}
export interface SeasonProgressionOut {
  player_type: "skater" | "goalie"; player_id: number; player_name: string;
  team_id: number | null;
  age_before: number; age_after: number;
  overall_before: number; overall_after: number;
  potential: number; development_type: string; summary_reason: string;
  events: DevelopmentEventOut[];
}
export interface DevelopmentSummary {
  season_id: number; progressions: SeasonProgressionOut[];
}
export interface StartNextSeasonResponse {
  new_season_id: number; development_summary: DevelopmentSummary;
}
export interface PlayerDevelopmentHistory {
  player_id: number; name: string; history: SeasonProgressionOut[];
}
export interface SkaterSeasonStats {
  season_id: number; gp: number; g: number; a: number; pts: number; sog: number;
}
export interface SkaterCareer {
  player_id: number; name: string; by_season: SkaterSeasonStats[]; totals: SkaterSeasonStats;
}
export interface GoalieSeasonStats {
  season_id: number; gp: number; shots_against: number; saves: number; goals_against: number; sv_pct: number;
}
export interface GoalieCareer {
  player_id: number; name: string; by_season: GoalieSeasonStats[]; totals: GoalieSeasonStats;
}

export type GameplanStyle = "balanced" | "offensive" | "defensive" | "physical";
export type GameplanLineUsage = "balanced" | "ride_top_lines" | "roll_all_lines";
export interface Gameplan {
  team_id: number;
  style: GameplanStyle;
  line_usage: GameplanLineUsage;
  editable: boolean;
}

export interface ApiError { error_code: string; message: string; }

export interface FreeAgentSkater {
  id: number; name: string; age: number; position: Position;
  potential: number; development_type: string;
  skating: number; shooting: number; passing: number; defense: number; physical: number;
  ovr: number;
}
export interface FreeAgentGoalie {
  id: number; name: string; age: number;
  potential: number; development_type: string;
  reflexes: number; positioning: number; rebound_control: number; puck_handling: number; mental: number;
  ovr: number;
}
export interface FreeAgentFilters {
  position?: Position;
  min_ovr?: number;
  min_potential?: number;
  max_age?: number;
  sort?: "ovr" | "potential" | "age" | "position";
  order?: "asc" | "desc";
}

export type PlayerKind = "skater" | "goalie";

export interface TradeBlockEntry {
  player_type: PlayerKind;
  player_id: number;
  team_id: number;
  team_name: string;
  team_abbreviation: string;
  name: string;
  age: number;
  position: string | null;
  ovr: number;
  asking_value: number;
  reason: string;
}

export interface TradeProposalRequest {
  target_player_type: PlayerKind;
  target_player_id: number;
  offered_player_type: PlayerKind;
  offered_player_id: number;
}

export interface TradeProposalResponse {
  accepted: boolean;
  message: string;
  error_code?: string | null;
  acquired_player_id?: number | null;
  acquired_player_type?: PlayerKind | null;
  traded_away_player_id?: number | null;
  traded_away_player_type?: PlayerKind | null;
}
