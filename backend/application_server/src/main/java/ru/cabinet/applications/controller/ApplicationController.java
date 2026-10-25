package ru.cabinet.applications.controller;

import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import ru.cabinet.applications.data.ApplicationStatus;
import ru.cabinet.applications.dto.ApplicationResponse;
import ru.cabinet.applications.dto.CounterOfferDecisionRequest;
import ru.cabinet.applications.dto.CreateApplicationRequest;
import ru.cabinet.applications.security.ClientPrincipal;
import ru.cabinet.applications.security.CurrentClient;
import ru.cabinet.applications.service.CreditApplicationService;

import java.net.URI;
import java.util.List;

@RestController
@RequestMapping("/api/v0/applications")
public class ApplicationController {

    private final CreditApplicationService service;

    public ApplicationController(CreditApplicationService service) {
        this.service = service;
    }

    @PostMapping
    public ResponseEntity<ApplicationResponse> create(@CurrentClient ClientPrincipal client,
                                                      @Valid @RequestBody CreateApplicationRequest request) {
        ApplicationResponse body = service.submit(client, request);
        return ResponseEntity.created(URI.create("/api/v0/applications/" + body.id())).body(body);
    }

    @GetMapping
    public List<ApplicationResponse> list(@CurrentClient ClientPrincipal client,
                                          @RequestParam(required = false) ApplicationStatus status) {
        return service.listOwned(client, status);
    }

    @GetMapping("/{id}")
    public ApplicationResponse get(@CurrentClient ClientPrincipal client, @PathVariable long id) {
        return service.getOwned(client, id);
    }

    @PostMapping("/{id}/counter-offer")
    public ApplicationResponse respondToCounterOffer(@CurrentClient ClientPrincipal client,
                                                     @PathVariable long id,
                                                     @Valid @RequestBody CounterOfferDecisionRequest request) {
        return service.respondToCounterOffer(client, id, request.accept());
    }
}
