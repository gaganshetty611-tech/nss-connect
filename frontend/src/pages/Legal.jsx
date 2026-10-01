import { Link } from 'react-router-dom'
import { CONTACT_EMAIL, LAST_UPDATED, SITE_NAME } from '../utils/site'

function LegalPage({ title, children }) {
  return (
    <article className="card mx-auto max-w-3xl p-6 sm:p-10">
      <h1 className="page-title">{title}</h1>
      <p className="mt-1 text-sm text-slate-500">Last updated: {LAST_UPDATED}</p>
      <div className="mt-6 space-y-6 text-sm leading-relaxed text-slate-700 [&_h2]:mb-2 [&_h2]:text-lg [&_h2]:font-semibold [&_ul]:list-disc [&_ul]:space-y-1 [&_ul]:pl-5">
        {children}
      </div>
    </article>
  )
}

export function Privacy() {
  return (
    <LegalPage title="Privacy Policy">
      <p>
        {SITE_NAME} connects NSS units, student volunteers and NGOs. This policy explains what personal data we collect, why we
        collect it and the choices you have. We handle personal data in line with India's Digital Personal Data Protection Act, 2023.
      </p>
      <section>
        <h2>What we collect and why</h2>
        <ul>
          <li><b>Account details</b> (name, email, password, phone, role): to create your account and let you sign in. Passwords are stored hashed, never in plain text.</li>
          <li><b>Profile details</b> (university, college, NSS unit, skills, interests, availability, optional photo): to match you with suitable drives and show your profile to organizers you apply to.</li>
          <li><b>Gender</b> (optional, "prefer not to say" is available): used only in aggregate NSS participation reports.</li>
          <li><b>Attendance records</b> (QR check-in and check-out times): to verify participation, calculate ABP hours and issue certificates.</li>
          <li><b>Event and NGO information</b> you submit, including verification documents (kept private and visible only to administrators): to verify organisations.</li>
          <li><b>Technical data</b> (IP address, browser, pages visited): for security, abuse prevention and, if you consent, analytics.</li>
        </ul>
      </section>
      <section>
        <h2>Cookies and analytics</h2>
        <p>
          We use an essential, HTTP-only cookie to keep you signed in. It is required for the site to work. If you click "Accept analytics",
          we also load Google Analytics to measure traffic in aggregate (IP addresses are anonymised). Analytics never loads unless you accept,
          and you can change your choice at any time using "Cookie settings" in the footer.
        </p>
      </section>
      <section>
        <h2>Use of AI</h2>
        <p>
          {SITE_NAME} uses AI-assisted features such as suggesting a drive category, recommending NSS units for a drive, estimating turnout and
          summarising drive details. By default these run on rules and statistics inside our own servers. If the administrator enables an external
          language-model provider (for example OpenAI or Google Gemini), the drive title, description and event details may be sent to that provider
          to generate a suggestion. We do not send your password, contact details or documents to AI providers. AI outputs are suggestions; people
          make the final decisions on approvals, attendance and certificates.
        </p>
      </section>
      <section>
        <h2>Who we share data with</h2>
        <ul>
          <li>Organizers of drives you apply to, and your NSS unit coordinators, can see the profile details needed to run the drive.</li>
          <li>Service providers that host the platform, send email and (if enabled) provide sign-in with Google, analytics or AI features, acting on our instructions.</li>
          <li>Anyone who knows a certificate ID can confirm that the certificate is genuine. The verification page shows only the details needed for that check.</li>
        </ul>
        <p className="mt-2">We do not sell your personal data.</p>
      </section>
      <section>
        <h2>Retention and security</h2>
        <p>
          We keep data while your account is active and as long as needed for NSS records and certificate verification, then delete or anonymise it.
          We use HTTPS, hashed passwords, short-lived access tokens, rate limiting and role-based access controls. No system is perfectly secure,
          so please use a strong, unique password.
        </p>
      </section>
      <section>
        <h2>Your rights</h2>
        <p>
          You can access, correct or delete your data, withdraw consent and raise a grievance by editing your profile or emailing{' '}
          <a className="font-semibold text-brand-700 underline" href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>. Children under 18 should use the
          platform only with the permission of a parent or guardian.
        </p>
      </section>
      <section>
        <h2>Changes</h2>
        <p>We will update this page when our practices change and show the new date above. See also our <Link className="font-semibold text-brand-700 underline" to="/terms">Terms &amp; Conditions</Link>.</p>
      </section>
    </LegalPage>
  )
}

export function Terms() {
  return (
    <LegalPage title="Terms & Conditions">
      <p>By creating an account or using {SITE_NAME} you agree to these terms. If you do not agree, please do not use the platform.</p>
      <section>
        <h2>Your account</h2>
        <ul>
          <li>Give accurate information and keep your password confidential. You are responsible for activity on your account.</li>
          <li>You must be old enough to consent under Indian law, or have a parent or guardian's permission.</li>
        </ul>
      </section>
      <section>
        <h2>Acceptable use</h2>
        <ul>
          <li>Do not post false, misleading, unlawful or offensive content, or impersonate another person, NGO or NSS unit.</li>
          <li>Do not fake attendance, share check-in QR codes with people who are not present, or tamper with certificates.</li>
          <li>Do not attempt to disrupt, scrape or gain unauthorised access to the platform.</li>
        </ul>
      </section>
      <section>
        <h2>NGOs, drives and volunteers</h2>
        <p>
          Drives are run by NGOs and NSS units, not by {SITE_NAME}. We verify organisations before they can post, but we cannot guarantee any drive.
          Volunteers take part at their own discretion and should follow the safety instructions of the organizer.
        </p>
      </section>
      <section>
        <h2>Certificates and ABP hours</h2>
        <p>
          Certificates and hours are issued only for attendance verified through the platform. We may withhold or revoke a certificate if the
          record turns out to be inaccurate or obtained by breaking these terms.
        </p>
      </section>
      <section>
        <h2>Content you upload</h2>
        <p>You keep ownership of what you upload but allow us to store and display it to run the platform. Only upload content you have the right to share.</p>
      </section>
      <section>
        <h2>Suspension and liability</h2>
        <p>
          We may suspend accounts that break these terms. The platform is provided "as is". To the extent permitted by law, we are not liable for
          indirect losses or for the acts of organizers, volunteers or third parties. These terms are governed by the laws of India.
        </p>
      </section>
      <section>
        <h2>Contact</h2>
        <p>
          Questions? Email <a className="font-semibold text-brand-700 underline" href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>. See also our{' '}
          <Link className="font-semibold text-brand-700 underline" to="/privacy">Privacy Policy</Link>.
        </p>
      </section>
    </LegalPage>
  )
}
