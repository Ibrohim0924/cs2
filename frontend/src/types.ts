export type User = {
  id: number;
  telegram_id: number;
  username: string;
  first_name: string;
  avatar_url?: string | null;
  level: number;
  xp: number;
  crystals: number;
  steam_connected: boolean;
  inventory_count: number;
  referral_count: number;
  referral_code: string;
  achievements: { slug: string; title: string; description: string; icon: string; unlocked: boolean }[];
}

export type CaseItem = {
  id: number;
  slug: string;
  name: string;
  description: string;
  image_url: string;
  price: number;
  is_free: boolean;
  published_reward_name: string;
};

export type InventoryItem = {
  id: number;
  name: string;
  weapon: string;
  image_url: string;
  exterior: string;
  float_value: number | null;
  status: string;
  acquired_at: string;
  development_data: boolean;
};

export type TaskItem = {
  id: number;
  slug: string;
  title: string;
  description: string;
  task_type: string;
  reward: number;
  status: string;
  verification_status: string;
};
