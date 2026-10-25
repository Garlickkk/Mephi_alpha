package ru.cabinet.applications.data;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface CreditApplicationRepository extends JpaRepository<CreditApplication, Long> {

    Optional<CreditApplication> findByIdAndClientLogin(Long id, String clientLogin);

    List<CreditApplication> findAllByClientLoginOrderByCreatedAtDesc(String clientLogin);

    List<CreditApplication> findAllByClientLoginAndStatusOrderByCreatedAtDesc(String clientLogin, ApplicationStatus status);
}
