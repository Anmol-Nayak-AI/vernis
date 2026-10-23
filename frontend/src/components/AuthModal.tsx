import { AnimatePresence, motion } from 'motion/react';
import { ArrowRight, LockKeyhole, Mail, UserRound, X } from 'lucide-react';
import { FormEvent, useState } from 'react';
import { useAuth } from '../context/AuthContext';

interface AuthModalProps { open: boolean; onClose: () => void; }

export function AuthModal({ open, onClose }: AuthModalProps) {
  const { signIn, signUp, signInWithGoogle, configured } = useAuth();
  const [mode, setMode] = useState<'signin' | 'signup'>('signin');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError('');
    try {
      if (mode === 'signin') await signIn(email, password);
      else await signUp(email, password, name);
      onClose();
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Authentication failed.'); }
    finally { setBusy(false); }
  };

  return <AnimatePresence>{open && <motion.div className="modal-backdrop" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onMouseDown={onClose}>
    <motion.section className="auth-modal" initial={{ opacity: 0, y: 18, scale: .98 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 12, scale: .98 }} transition={{ type: 'spring', stiffness: 320, damping: 28 }} onMouseDown={(event) => event.stopPropagation()}>
      <button className="modal-close" onClick={onClose}><X size={17} /></button>
      <div className="auth-art"><span /><span /><span /><div><small>Private atelier</small><strong>Your art, rights, provenance,<br />and commerce in one place.</strong></div></div>
      <div className="auth-form-wrap">
        <p className="kicker">Vernis membership</p>
        <h2>{mode === 'signin' ? 'Welcome back.' : 'Open your studio.'}</h2>
        <p>{mode === 'signin' ? 'Sign in to access your private archive and marketplace.' : 'Create an identity for your practice and your team.'}</p>
        {!configured && <div className="config-notice"><LockKeyhole size={14} /> Add Supabase environment variables to enable live authentication.</div>}
        <form onSubmit={submit}>
          {mode === 'signup' && <label><UserRound size={15} /><input required value={name} onChange={(event) => setName(event.target.value)} placeholder="Studio or artist name" /></label>}
          <label><Mail size={15} /><input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@studio.com" /></label>
          <label><LockKeyhole size={15} /><input required minLength={8} type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Password" /></label>
          {error && <div className="auth-error">{error}</div>}
          <button className="auth-submit" disabled={busy || !configured}>{busy ? 'Please wait…' : mode === 'signin' ? 'Enter studio' : 'Create studio'} <ArrowRight size={15} /></button>
        </form>
        <div className="auth-divider"><span>or</span></div>
        <button className="google-auth" disabled={!configured} onClick={() => signInWithGoogle().catch((reason) => setError(reason.message))}>Continue with Google</button>
        <button className="auth-mode" onClick={() => { setMode(mode === 'signin' ? 'signup' : 'signin'); setError(''); }}>{mode === 'signin' ? 'New to Vernis? Create a studio' : 'Already a member? Sign in'}</button>
      </div>
    </motion.section>
  </motion.div>}</AnimatePresence>;
}
