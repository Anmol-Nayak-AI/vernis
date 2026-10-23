import { ArrowRight, LockKeyhole, Mail, UserRound } from 'lucide-react';
import { FormEvent, useState } from 'react';
import { useAuth } from '../../context/AuthContext';

export function AuthenticationGate() {
  const { signIn, signUp, signInWithGoogle } = useAuth();
  const [mode, setMode] = useState<'signin' | 'signup'>('signin');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    setNotice('');
    try {
      if (mode === 'signin') await signIn(email, password);
      else {
        await signUp(email, password, name);
        setNotice('Account created. If email confirmation is enabled, use the link in your inbox to continue.');
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Authentication failed.');
    } finally {
      setBusy(false);
    }
  };

  return <main className="v2-gate">
    <section className="v2-onboarding-card v2-auth-card">
      <div className="v2-onboarding-mark"><LockKeyhole /></div>
      <p className="v2-kicker">Protected workspace</p>
      <h1>{mode === 'signin' ? 'Enter Vernis.' : 'Create your account.'}</h1>
      <p>Authentication protects organization-scoped artwork records, evidence, and private assets.</p>
      <form onSubmit={submit}>
        {mode === 'signup' && <label><span>Name</span><span className="v2-input-with-icon"><UserRound /><input required value={name} onChange={(event) => setName(event.target.value)} autoComplete="name" /></span></label>}
        <label><span>Email</span><span className="v2-input-with-icon"><Mail /><input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" /></span></label>
        <label><span>Password</span><span className="v2-input-with-icon"><LockKeyhole /><input required minLength={8} type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete={mode === 'signin' ? 'current-password' : 'new-password'} /></span></label>
        {error && <div className="v2-form-error" role="alert">{error}</div>}
        {notice && <div className="v2-form-notice" role="status">{notice}</div>}
        <button className="v2-primary" disabled={busy}>{busy ? 'Please wait…' : mode === 'signin' ? 'Sign in' : 'Create account'} <ArrowRight /></button>
      </form>
      <div className="v2-auth-alternatives"><span>or</span><button type="button" onClick={() => signInWithGoogle().catch((reason) => setError(reason instanceof Error ? reason.message : 'Google sign-in failed.'))}>Continue with Google</button><button type="button" onClick={() => { setMode(mode === 'signin' ? 'signup' : 'signin'); setError(''); setNotice(''); }}>{mode === 'signin' ? 'New to Vernis? Create an account' : 'Already have an account? Sign in'}</button></div>
    </section>
  </main>;
}
