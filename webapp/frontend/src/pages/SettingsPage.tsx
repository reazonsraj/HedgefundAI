import { useEffect, useState } from "react";
import { api } from "@/services/api";
import type { ApiKeyStatus } from "@/types";
import { Eye, EyeOff, Save } from "lucide-react";

export function SettingsPage() {
  const [keys, setKeys] = useState<ApiKeyStatus[]>([]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [visible, setVisible] = useState<Record<string, boolean>>({});
  const [saved, setSaved] = useState(false);

  useEffect(() => { api.config.apiKeys().then(setKeys); }, []);

  const handleSave = async () => {
    const nonEmpty = Object.fromEntries(Object.entries(values).filter(([, v]) => v));
    if (Object.keys(nonEmpty).length === 0) return;
    await api.config.updateApiKeys(nonEmpty);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
    api.config.apiKeys().then(setKeys);
    setValues({});
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Settings</h1>
      <div className="bg-[#111] border border-[#222] rounded-lg p-4">
        <h2 className="text-sm font-medium text-[#999] mb-4">API Keys</h2>
        <div className="space-y-3">
          {keys.map((k) => (
            <div key={k.env_var} className="flex items-center gap-3">
              <div className="w-32">
                <span className="text-sm">{k.provider}</span>
                {k.is_set && <span className="ml-2 text-xs text-[#22c55e]">Set</span>}
              </div>
              <div className="flex-1 relative">
                <input type={visible[k.env_var] ? "text" : "password"} placeholder={k.is_set ? "********" : "Enter API key"} value={values[k.env_var] || ""} onChange={(e) => setValues({ ...values, [k.env_var]: e.target.value })} className="w-full bg-[#0a0a0a] border border-[#222] rounded px-3 py-2 text-sm text-white placeholder-[#666] focus:outline-none focus:border-[#6366f1]" />
                <button onClick={() => setVisible({ ...visible, [k.env_var]: !visible[k.env_var] })} className="absolute right-2 top-1/2 -translate-y-1/2 text-[#666]">{visible[k.env_var] ? <EyeOff size={14} /> : <Eye size={14} />}</button>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-4 flex items-center gap-3">
          <button onClick={handleSave} className="bg-[#6366f1] hover:bg-[#5558e6] text-white px-4 py-2 rounded-lg text-sm flex items-center gap-2"><Save size={14} /> Save Keys</button>
          {saved && <span className="text-sm text-[#22c55e]">Saved!</span>}
        </div>
      </div>
    </div>
  );
}
