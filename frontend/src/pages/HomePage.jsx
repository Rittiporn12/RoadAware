import Header from "../components/layout/Header";
import Footer from "../components/layout/Footer";
import Hero from "../features/home/components/Hero";
import FeatureCards from "../features/home/components/FeatureCards";
import GettingStarted from "../features/home/components/GettingStarted";
export default function HomePage() {
  return (
    <>
      <Header />
      <main id="main-content">
        <Hero />
        <FeatureCards />
        <GettingStarted />
      </main>
      <Footer />
    </>
  );
}
