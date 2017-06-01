import { Component, OnInit } from '@angular/core';
import { Http } from '@angular/http';

import { PortfolioService } from './portfolio.service';

@Component({
    selector: 'app-root',
    templateUrl: './portfolio-list.component.html',
    styleUrls: ['./app.component.css'],
    providers: [PortfolioService]
})
export class PortfolioListComponent implements OnInit {
    records;

    constructor(private portfolioService: PortfolioService) {}

    ngOnInit(): void {
        this.records = this.portfolioService.getRecords().map(v => v['records']);
    }
}

