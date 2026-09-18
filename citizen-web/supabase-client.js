// Shared Supabase client - both auth.js and script.js use this same connection.
// Get these two values from: Supabase dashboard -> Project Settings -> API
const SUPABASE_URL ="https://ltrlcxotixvpuikgzgty.supabase.co";
const SUPABASE_ANON_KEY ="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx0cmxjeG90aXh2cHVpa2d6Z3R5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODkwNDA3MzQsImV4cCI6MjEwNDYxNjczNH0.6sjK655B3s_MXba-56srTISFlVG_FDB8w2b05aUe1As";

const supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
