import { Component } from '@angular/core';
import { Http } from '@angular/http';

import { DartService } from './dart.service';

@Component({
  selector: 'app-root',
  templateUrl: './listdart.component.html',
  styleUrls: ['./app.component.css'],
  providers: [DartService]
})
export class ListDartComponent {
  records;

  constructor(private dartService: DartService) {
    this.records = dartService.getRecords().map(v => v['records'])
  }
}
